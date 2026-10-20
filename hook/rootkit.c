#include <linux/init.h>
#include <linux/module.h>
#include <linux/kernel.h>
#include <linux/slab.h>
#include <linux/uaccess.h>
#include <linux/fs.h>
#include <linux/fdtable.h> // 包含文件描述符表相关定义
#include <linux/path.h>    // 路径相关定义
#include <linux/syscalls.h>
#include <linux/version.h>
#include <linux/namei.h>
#include <linux/sched.h>
#include <linux/hashtable.h>
#include <linux/fs_struct.h>
#include <linux/nsproxy.h>
#include <linux/mutex.h>
#include <linux/vfs.h>

#include "ftrace_helper.h"
#include "log_hook.h"
#include "write_log.h"

MODULE_LICENSE("GPL");
MODULE_AUTHOR("TheXcellerator");
MODULE_DESCRIPTION("write syscall hook");
MODULE_VERSION("0.01");

#if defined(CONFIG_X86_64) && (LINUX_VERSION_CODE >= KERNEL_VERSION(4, 17, 0))
#define PTREGS_SYSCALL_STUBS 1
#endif

#if defined(CONFIG_X86_64) && (LINUX_VERSION_CODE >= KERNEL_VERSION(5, 0, 0))
#define X64_SYSCALL 1
#endif

static DEFINE_MUTEX(log_mutex);
static size_t mnt_ns_id[CONTAINER_NUMS];
static struct workqueue_struct *log_wq;

struct mnt_namespace *get_mnt_ns_by_pid(pid_t pid)
{
    struct pid *vpid;
    struct task_struct *task;
    struct mnt_namespace *mnt_ns = NULL;

    vpid = find_get_pid(pid);

    if (!vpid)
        goto out;

    task = pid_task(vpid, PIDTYPE_PID);
    if (!task || !task->nsproxy)
        goto put_pid;

    mnt_ns = task->nsproxy->mnt_ns;
put_pid:
    put_pid(vpid);
out:
    return mnt_ns;
}

static bool is_from_container(int *current_container)
{
    size_t cur_mnt_ns = (size_t)current->nsproxy->mnt_ns;
    int i = 0;

    for (i = 0; i < CONTAINER_NUMS; ++i)
    {
        if (mnt_ns_id[i] == cur_mnt_ns)
        {
            *current_container = i;
            return true;
        }
    }
    *current_container = -1;
    return false;
}

#ifdef PTREGS_SYSCALL_STUBS
static asmlinkage long (*orig_write)(const struct pt_regs *);
asmlinkage int hook_write(const struct pt_regs *regs)
{
    int fd = regs->di;                   // 文件描述符
    char __user *buf = (char *)regs->si; // 写入缓冲区
    size_t count = regs->dx;             // 字节数
#else
static asmlinkage long (*orig_write)(unsigned int fd, const char __user *buf, size_t count);

asmlinkage int hook_write(unsigned int fd, const char __user *buf, size_t count)
{
#endif
    char *kernel_buf;                  // 内核缓冲区
    struct log_work *log_entry = NULL; // 日志工作结构体
    int i = 0, ret = 0;
    struct file *file = NULL; // 文件对象
    struct path *path = NULL; // 文件路径
    char *pathname = NULL;    // 文件路径名
    char *tmp_buf = NULL;     // 临时缓冲区
    int current_container = -1;

    // 过滤掉非容器内的进程
    if (!is_from_container(&current_container))
    {
        return orig_write(regs);
    }
    if (current_container < 0 || current_container >= CONTAINER_NUMS)
    {
        return orig_write(regs);
    }
    // 检查 buf 是否可访问，并且 count 必须有效
    if (!buf || !access_ok(buf, count))
    {
        printk(KERN_INFO "rootkit: invalid buffer\n");

        return orig_write(regs);
    }

    // 通过文件描述符获取文件对象
    file = fget(fd);
    if (!file)
        return orig_write(regs);

    // 过滤掉除了文件和目录之外的文件类型（如管道、套接字、字符设备等）
    if (!S_ISREG(file->f_inode->i_mode) && !S_ISDIR(file->f_inode->i_mode))
    {
        fput(file);
        return orig_write(regs);
    }

    log_entry = kmalloc(sizeof(struct log_work), GFP_KERNEL);
    if (!log_entry)
    {
        printk(KERN_INFO "rootkit: memory allocation failed\n");
        fput(file);
        return orig_write(regs);
    }

    // 获取文件路径
    path = &file->f_path;
    tmp_buf = (char *)__get_free_page(GFP_KERNEL);
    if (tmp_buf)
    {
        pathname = d_path(path, tmp_buf, PAGE_SIZE);
        if (!IS_ERR(pathname))
        {
            strncpy(log_entry->filepath, pathname, sizeof(log_entry->filepath) - 1);
        }
        free_page((unsigned long)tmp_buf);
    }
    // 获取文件偏移量
    if (file->f_flags & O_APPEND)
    {
        log_entry->file_pos = file->f_inode->i_size;
    }
    else
    {
        log_entry->file_pos = file->f_pos;
    }
    fput(file);
    if (strlen(log_entry->filepath) == 0)
    {
        kfree(log_entry);
        return orig_write(regs);
    }

    // 分配内存
    kernel_buf = kmalloc(count, GFP_KERNEL);
    log_entry->hex_buf = kmalloc(count * 2 + 1, GFP_KERNEL); // 每个字节转 2 个十六进制字符
    if (!kernel_buf || !log_entry->hex_buf)
    {
        printk(KERN_INFO "rootkit: memory allocation failed\n");
        kfree(kernel_buf);
        kfree(log_entry->hex_buf);
        kfree(log_entry);
        return orig_write(regs);
    }

    // 从用户空间拷贝数据
    if (copy_from_user(kernel_buf, buf, count))
    {
        kfree(kernel_buf);
        kfree(log_entry->hex_buf);
        kfree(log_entry);
        printk(KERN_INFO "rootkit: copy_from_user failed\n");
        return orig_write(regs);
    }

    // 转换为十六进制字符串
    for (i = 0; i < count; i++)
        snprintf(log_entry->hex_buf + i * 2, 3, "%02X", (unsigned char)kernel_buf[i]);
    log_entry->hex_buf[count * 2] = '\n'; // 添加换行符
    log_entry->count = count;

    log_entry->nsproxy = current->nsproxy;

#ifdef PTREGS_SYSCALL_STUBS
    ret = orig_write(regs);
#else
    ret = orig_write(fd, buf, count);
#endif
    // 获取时间戳
    ktime_get_real_ts64(&log_entry->ts);
    log_entry->container_index = current_container;

    // 提交工作
    // printk(KERN_INFO "rootkit: log write work submitted, %s, %zu, %lld%09ld\n", log_entry->filepath, log_entry->count, log_entry->ts.tv_sec, log_entry->ts.tv_nsec);
    INIT_WORK(&log_entry->work, log_write_fn);
    queue_work(log_wq, &log_entry->work);

    kfree(kernel_buf);
    return ret;
}

static struct ftrace_hook hooks[] = {
#ifdef X64_SYSCALL
    HOOK("__x64_sys_write", hook_write, &orig_write),
#else
    HOOK("sys_write", hook_write, &orig_write),
#endif
};

static int __init rootkit_init(void)
{
    int err, i;
    // 获取容器的挂载命名空间
    for (i = 0; i < CONTAINER_NUMS; ++i)
    {
        mnt_ns_id[i] = (size_t)get_mnt_ns_by_pid(container_pids[i]);
    }

    // 安装钩子
    err = fh_install_hooks(hooks, ARRAY_SIZE(hooks));
    if (err)
        return err;

    // 创建工作队列
    log_wq = create_singlethread_workqueue("log_wq");
    if (!log_wq)
    {
        printk(KERN_ERR "Failed to create workqueue\n");
        return -ENOMEM;
    }
    printk(KERN_INFO "rootkit: loaded\n");
    return 0;
}

static void __exit rootkit_exit(void)
{
    fh_remove_hooks(hooks, ARRAY_SIZE(hooks));
    destroy_workqueue(log_wq);
    printk(KERN_INFO "rootkit: unloaded\n");
}

module_init(rootkit_init);
module_exit(rootkit_exit);