#ifndef WRITE_LOG_H
#define WRITE_LOG_H

#include <linux/module.h>
#include <linux/kernel.h>
#include <linux/init.h>
#include <linux/workqueue.h>
#include <linux/fs.h>
#include <linux/kallsyms.h>
#include <linux/uaccess.h>

#include "log_hook.h"

struct log_work
{
    struct work_struct work;
    char filepath[4096];
    int container_index;
    char *hex_buf;
    off_t file_pos;
    struct timespec64 ts;
    size_t count;
    struct nsproxy *nsproxy;
};

void log_write_fn(struct work_struct *work)
{
    struct log_work *log_entry = container_of(work, struct log_work, work);
    struct file *log_file;
    struct tm tm;
    loff_t pos = 0;
    char file_pos_buf[32] = {0}; // 文件偏移量字符串
    char ts_buf[32] = {0};       // 时间戳字符串
    char log_file_path[128] = {0};
    if(log_entry->container_index != 0) {
        printk(KERN_INFO "rootkit: log write work running, %s, %zu, %lld%09ld, container_index: %d\n", log_entry->filepath, log_entry->count, log_entry->ts.tv_sec, log_entry->ts.tv_nsec, log_entry->container_index);
    }
    snprintf(log_file_path, sizeof(log_file_path), "%s/%s.log", LOG_DIR, container_ids[log_entry->container_index]);

    // printk(KERN_INFO "rootkit: log write work running, %s, %zu, %lld%09ld, log_file: %s\n", log_entry->filepath, log_entry->count, log_entry->ts.tv_sec, log_entry->ts.tv_nsec, log_file_path);

    // 打开日志文件
    log_file = filp_open(log_file_path, O_WRONLY | O_CREAT | O_APPEND, 0777);
    if (IS_ERR(log_file))
    {
        long err = PTR_ERR(log_file);
        printk(KERN_ERR "Failed to open log file: Error code %ld\n", err);
        kfree(log_entry->hex_buf); // 释放十六进制缓冲区内存
        kfree(log_entry);          // 释放工作结构体
        return;
    }

    time64_to_tm(log_entry->ts.tv_sec, 0, &tm);
    snprintf(file_pos_buf, sizeof(file_pos_buf), "%ld", log_entry->file_pos);
    // snprintf(ts_buf, sizeof(ts_buf), "%lld%09ld", log_entry->ts.tv_sec, log_entry->ts.tv_nsec);
    snprintf(ts_buf, sizeof(ts_buf), "%04d-%02d-%02d %02d:%02d:%02d.%09lu", tm.tm_year + 1900, tm.tm_mon + 1, tm.tm_mday, tm.tm_hour, tm.tm_min, tm.tm_sec, log_entry->ts.tv_nsec);
    kernel_write(log_file, ts_buf, strlen(ts_buf), &pos);
    kernel_write(log_file, ",", 1, &pos);
    kernel_write(log_file, log_entry->filepath, strlen(log_entry->filepath), &pos);
    kernel_write(log_file, ",", 1, &pos);
    kernel_write(log_file, file_pos_buf, strlen(file_pos_buf), &pos);
    kernel_write(log_file, ",", 1, &pos);
    kernel_write(log_file, log_entry->hex_buf, log_entry->count * 2 + 1, &pos);

    // 关闭日志文件
    filp_close(log_file, NULL);

    // 释放内存
    kfree(log_entry->hex_buf); // 释放十六进制缓冲区内存
    kfree(log_entry);          // 释放工作结构体
}
#endif
