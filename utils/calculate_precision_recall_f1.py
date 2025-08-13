import json
import os
import re

env = "CVE-2019-14234" # or "CVE-2023-31047"
answer_type = "db" # or "fs"

answer_path = os.path.join(env, "answers.json")
predictions_path = "webfix-matchare/predictions.json"
try:
    with open(answer_path, "r") as f:
        answers = json.load(f)
    with open(predictions_path, "r") as f:
        predictions = json.load(f)
except:
    print(f"Error loading files: {answer_path} or {predictions_path}")


def check_db_statement(answer, prediction, check_columns: dict[str, list] | None=None) -> bool:
    if answer["type"] != prediction["type"] \
    or answer["table"] != prediction["table"] :
        return False
    
    if not check_columns and len(answer["columns"]) != len(prediction["columns"]):
        return False

    if check_columns is None:
        check_columns = list(answer["columns"].keys())
    else:
        cols = check_columns.get(f"{answer['type']}.{answer['table']}", None)
        check_columns = cols if cols is not None else list(answer["columns"].keys())

    for key in check_columns:
        value = answer["columns"].get(key, "*")
        if value == "*":
            continue
        if key not in prediction["columns"]:
            return False
        if prediction["columns"][key] != value:
            return False
    
    return True


def wildcard_match(pattern: str | None, string: str | None) -> bool:
    """
    判断字符串 string 是否匹配 pattern，其中 pattern 可以包含通配符 '*'
    """
    if pattern is None or string is None:
        return pattern == string

    # 如果不包含 *，直接判断相等
    if '*' not in pattern:
        return pattern == string
    
    # 转义正则中其它特殊字符，只保留 * 作为通配符
    escaped = re.escape(pattern)
    # 把转义后的 \* 替换为 .*
    regex_pattern = '^' + escaped.replace(r'\*', '.*') + '$'
    
    return re.match(regex_pattern, string) is not None


def check_fs_operation(answer, prediction) -> bool:
    if answer["operation"] != prediction["operation"] \
    or not wildcard_match(answer["source_path"], prediction["source_path"]) \
    or not wildcard_match(answer["destination_path"], prediction["destination_path"]) \
    or answer["is_directory"] != prediction["is_directory"]:
        # print(f"Mismatch: {answer} vs {prediction}")
        return False

    return True


def check_single_request(answer, prediction, answer_type) -> bool:
    if answer_type == "db":
        answer = answer["db_statements"]
        prediction = prediction["db_statements"]

        all_p = len(answer)
        true_p = 0
        pre_p = len(prediction)
        check_columns = None
        # For CVE-2024-38856, we need to check the columns
        # check_columns = {
        #     "INSERT.public.NOTE_DATA": ["NOTE_INFO", "MORE_INFO_URL"],
        #     "INSERT.public.SERVER_HIT": ["CONTENT_ID"],
        # }
        # For CVE-2021-26120, we need to check the columns
        # check_columns = {
        #     "INSERT.cms_content": ["content_id", "content_name", "content_alias", "type",
        #                            "owner_id", "parent_id", "template_id", "active", "last_modified_by"],
        #     "INSERT.cms_content_props": ["content_id", "type", "prop_name", "content"],
        #     "INSERT.cms_adminlog": ["user_id", "username", "item_id", "item_name", "action", "ip_addr"],
        #     "UPDATE.cms_content": ["content_id", "content_name", "content_alias", "type",
        #                            "owner_id", "parent_id", "template_id", "active", "show_in_menu"],
        #     "UPDATE.cms_content_props": ["content_id", "prop_name", "content"],
        #     "DELETE.cms_content": ["content_id"],
        # }
        # # For CVE-2015-8562
        # check_columns = {
        #     "INSERT.j_content": ["id", "title", "alias", "introtext", "fulltext",
        #                          "catid", "images", "urls", "attribs", "access", "metadata"],
        #     "INSERT.j_ucm_history": ["ucm_item_id", "ucm_type_id", "editor_user_id"],
        #     "UPDATE.j_content": ["id", "title", "alias", "introtext", "catid", "access", "state"],
        #     "DELETE.j_contentitem_tag_map": ["type_alias", "content_item_id"],
        #     "DELETE.j_ucm_history": ["ucm_item_id", "ucm_type_id"],
        #     "DELETE.j_content": ["id"],
        # }
        def is_true_positive(prediction):
            for i in range(len(answer)):
                if check_db_statement(answer[i], prediction, check_columns):
                    return True
            return False
        for i in range(len(prediction)):
            if is_true_positive(prediction[i]):
                true_p += 1
        
        return all_p, true_p, pre_p
    
    elif answer_type == "fs":
        # if "fs_operations" not in answer:
        #     if len(prediction["fs_operations"]) == 0:
        #         return True
        #     else: 
        #         return False
        # answer = answer["fs_operations"]
        # prediction = prediction["fs_operations"]

        # if len(answer) != len(prediction):
        #     print(f"Length mismatch: {len(answer)} vs {len(prediction)}")
        #     return False
        # for i in range(len(answer)):
        #     if not check_fs_operation(answer[i], prediction[i]):
        #         return False
        all_p = len(answer["fs_operations"])
        true_p = 0
        pre_p = len(prediction["fs_operations"])
        def is_true_positive(prediction):
            for i in range(len(answer["fs_operations"])):
                if check_fs_operation(answer["fs_operations"][i], prediction):
                    return True
            return False
        for i in range(len(prediction["fs_operations"])):
            if is_true_positive(prediction["fs_operations"][i]):
                true_p += 1
        
        return all_p, true_p, pre_p


def calculate_accuracy() -> float:
    all_ps = 0
    true_ps = 0
    pre_ps = 0

    for x_request_id, answer in answers.items():
        if x_request_id not in predictions:
            print(f"{x_request_id} not in predictions, {len(answer)}")
            continue
        prediction = predictions[x_request_id]
        all_p, true_p, pre_p = check_single_request(answer, prediction, answer_type)
        all_ps += all_p
        true_ps += true_p
        pre_ps += pre_p

    precision = true_ps / pre_ps if pre_ps > 0 else 0.0
    recall = true_ps / all_ps if all_ps > 0 else 0.0
    f1_score = 2 * (precision * recall) / (precision + recall) if ((precision + recall) != 0) else 0

    return precision, recall, f1_score


if __name__ == "__main__":
    precision, recall, f1_score = calculate_accuracy()
    print(f"Precision: {precision:.4f}, Recall: {recall:.4f}, F1 Score: {f1_score:.4f}")