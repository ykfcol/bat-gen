# -*- coding: utf-8 -*-
"""
角色文件替换工具（命令行版）
功能：管理角色集合，一键将角色文件夹内容覆盖到用户指定的目标路径
支持 Python 2.7+ / 3.x
"""

import os
import sys
import json
import shutil

# 默认角色集合
DEFAULT_ROLES = [
    "孔雀", "白骨", "罗刹", "夜叉", "牛魔王", "百花羞",
    "百年猪妖", "羊头怪", "狮子", "虫子", "刑天", "刺猬", "猪", "熊"
]

# 配置文件名
CONFIG_FILE = "config.json"


def get_base_path():
    """获取程序运行的基础路径（兼容打包后的exe）"""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def load_config():
    """加载配置文件"""
    config_path = os.path.join(get_base_path(), CONFIG_FILE)
    try:
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                return config
    except Exception as e:
        print("[错误] 配置加载失败: %s" % str(e))

    return {
        "collection_name": "野外+超级集合",
        "roles": DEFAULT_ROLES[:],
        "target_path": ""
    }


def save_config(config):
    """保存配置文件"""
    config_path = os.path.join(get_base_path(), CONFIG_FILE)
    try:
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print("[错误] 配置保存失败: %s" % str(e))


def copy_role_files(role_name, target_path):
    """
    将角色文件夹的内容覆盖复制到目标路径
    :param role_name: 角色名称
    :param target_path: 目标路径
    :return: (success, message)
    """
    base_path = get_base_path()
    role_dir = os.path.join(base_path, role_name)

    if not os.path.exists(role_dir):
        return False, "角色文件夹不存在: " + role_dir

    if not os.path.exists(target_path):
        return False, "目标路径不存在: " + target_path

    try:
        copied_count = 0
        for item in os.listdir(role_dir):
            src = os.path.join(role_dir, item)
            dst = os.path.join(target_path, item)

            if os.path.isfile(src):
                shutil.copy2(src, dst)
                copied_count += 1
            elif os.path.isdir(src):
                if os.path.exists(dst):
                    shutil.rmtree(dst)
                shutil.copytree(src, dst)
                copied_count += 1

        msg = "[%s] 替换完成，共复制 %d 个项目" % (role_name, copied_count)
        return True, msg

    except Exception as e:
        return False, "复制失败: " + str(e)


def generate_bat(role_name, target_path):
    """生成角色对应的bat脚本内容"""
    bat_content = '@echo off\n'
    bat_content += 'chcp 65001 >nul\n'
    bat_content += 'echo.\n'
    bat_content += 'echo ========================================\n'
    bat_content += 'echo   正在将【%s】的文件覆盖到目标路径\n' % role_name
    bat_content += 'echo ========================================\n'
    bat_content += 'echo.\n'
    bat_content += 'echo 源路径: %%~dp0%s\\\n' % role_name
    bat_content += 'echo 目标路径: %s\\\n' % target_path
    bat_content += 'echo.\n'
    bat_content += '\n'
    bat_content += 'if not exist "%%~dp0%s\\" (\n' % role_name
    bat_content += '    echo [错误] 角色文件夹不存在！\n'
    bat_content += '    pause\n'
    bat_content += '    exit /b 1\n'
    bat_content += ')\n'
    bat_content += '\n'
    bat_content += 'if not exist "%s\\" (\n' % target_path
    bat_content += '    echo [错误] 目标路径不存在！\n'
    bat_content += '    pause\n'
    bat_content += '    exit /b 1\n'
    bat_content += ')\n'
    bat_content += '\n'
    bat_content += 'xcopy "%%~dp0%s\\*" "%s\\" /E /Y /Q\n' % (role_name, target_path)
    bat_content += 'echo.\n'
    bat_content += 'echo [完成] 【%s】文件替换成功！\n' % role_name
    bat_content += 'pause\n'
    return bat_content


def generate_all(config):
    """一键生成所有bat脚本和角色文件夹"""
    base_path = get_base_path()
    target_path = config.get("target_path", "")
    roles = config.get("roles", [])

    if not target_path:
        return False, "请先设置目标路径！"

    results = []
    for role in roles:
        # 创建角色文件夹
        role_dir = os.path.join(base_path, role)
        if not os.path.exists(role_dir):
            os.makedirs(role_dir)

        # 生成bat脚本
        bat_content = generate_bat(role, target_path)
        bat_path = os.path.join(base_path, role + ".bat")
        with open(bat_path, 'w', encoding='utf-8') as f:
            f.write(bat_content)
        results.append("  [OK] " + role)

    msg = "生成完成！共 %d 个角色:\n" % len(roles) + "\n".join(results)
    return True, msg


def save_to_role(role_name, target_path, config):
    """
    将目标路径的文件保存到角色文件夹（反向操作）
    如果角色文件夹已存在则清空后覆盖
    如果角色不在列表中则自动添加
    :param role_name: 角色名称（即保存的文件夹名）
    :param target_path: 目标路径（源）
    :param config: 配置字典
    :return: (success, message)
    """
    base_path = get_base_path()
    role_dir = os.path.join(base_path, role_name)

    if not os.path.exists(target_path):
        return False, "目标路径不存在: " + target_path

    # 检查目标路径是否有文件
    items = os.listdir(target_path)
    if not items:
        return False, "目标路径为空，没有可保存的文件"

    try:
        # 如果角色文件夹已存在，清空它
        if os.path.exists(role_dir):
            shutil.rmtree(role_dir)

        # 创建角色文件夹
        os.makedirs(role_dir)

        # 将目标路径的内容复制到角色文件夹
        copied_count = 0
        for item in items:
            src = os.path.join(target_path, item)
            dst = os.path.join(role_dir, item)

            if os.path.isfile(src):
                shutil.copy2(src, dst)
                copied_count += 1
            elif os.path.isdir(src):
                shutil.copytree(src, dst)
                copied_count += 1

        # 如果角色不在列表中，自动添加
        if role_name not in config["roles"]:
            config["roles"].append(role_name)
            save_config(config)

        msg = "[保存成功] 目标路径 -> 【%s】，共 %d 个项目" % (role_name, copied_count)
        return True, msg

    except Exception as e:
        return False, "保存失败: " + str(e)


def clear_screen():
    """清屏"""
    os.system('cls' if os.name == 'nt' else 'clear')


def show_menu(config):
    """显示主菜单"""
    print("")
    print("=" * 50)
    print("  角色文件替换工具 - %s" % config["collection_name"])
    print("=" * 50)
    print("")
    print("  目标路径: %s" % (config["target_path"] if config["target_path"] else "(未设置)"))
    print("")
    print("  --- 角色列表 ---")
    roles = config.get("roles", [])
    for i, role in enumerate(roles):
        print("  %2d. %s" % (i + 1, role))
    print("")
    print("  --- 操作 ---")
    print("  [S] 设置目标路径")
    print("  [G] 一键生成所有BAT和文件夹")
    print("  [A] 添加角色")
    print("  [D] 删除角色")
    print("  [R] 输入编号执行替换")
    print("  [W] 保存：将目标路径文件保存到角色文件夹")
    print("  [Q] 退出")
    print("")


def input_text(prompt):
    """兼容 Python 2/3 的输入"""
    try:
        return raw_input(prompt)
    except NameError:
        return input(prompt)


def main():
    """主程序入口"""
    config = load_config()

    while True:
        clear_screen()
        show_menu(config)

        choice = input_text("请输入操作: ").strip().upper()

        if choice == 'S':
            # 设置目标路径
            print("")
            path = input_text("请输入目标路径 (直接粘贴文件夹路径): ").strip()
            if path:
                # 去掉可能的引号
                path = path.strip('"').strip("'")
                if os.path.exists(path):
                    config["target_path"] = path
                    save_config(config)
                    print("\n[OK] 目标路径已设置: %s" % path)
                else:
                    print("\n[警告] 路径不存在，但已保存。请确保使用时路径存在。")
                    config["target_path"] = path
                    save_config(config)
            else:
                print("\n[取消] 未输入路径")
            input_text("\n按回车继续...")

        elif choice == 'G':
            # 一键生成
            if not config["target_path"]:
                print("\n[错误] 请先设置目标路径！")
                input_text("\n按回车继续...")
                continue

            success, msg = generate_all(config)
            print("")
            print(msg)
            input_text("\n按回车继续...")

        elif choice == 'A':
            # 添加角色
            print("")
            name = input_text("请输入新角色名称: ").strip()
            if not name:
                print("[取消] 未输入名称")
            elif name in config["roles"]:
                print("[错误] 角色 [%s] 已存在！" % name)
            else:
                config["roles"].append(name)
                save_config(config)
                print("[OK] 已添加角色: %s" % name)
            input_text("\n按回车继续...")

        elif choice == 'D':
            # 删除角色
            print("")
            roles = config.get("roles", [])
            if not roles:
                print("[提示] 没有可删除的角色")
                input_text("\n按回车继续...")
                continue

            nums = input_text("请输入要删除的角色编号 (多个用逗号分隔): ").strip()
            if not nums:
                print("[取消]")
                input_text("\n按回车继续...")
                continue

            try:
                indices = [int(x.strip()) - 1 for x in nums.split(",")]
                names_to_delete = []
                for idx in indices:
                    if 0 <= idx < len(roles):
                        names_to_delete.append(roles[idx])
                    else:
                        print("[警告] 编号 %d 无效，跳过" % (idx + 1))

                if names_to_delete:
                    print("将删除: %s" % ", ".join(names_to_delete))
                    confirm = input_text("确认删除？(Y/N): ").strip().upper()
                    if confirm == 'Y':
                        for name in names_to_delete:
                            config["roles"].remove(name)
                        save_config(config)
                        print("[OK] 已删除 %d 个角色" % len(names_to_delete))
                    else:
                        print("[取消]")
            except ValueError:
                print("[错误] 请输入有效的数字编号")
            input_text("\n按回车继续...")

        elif choice == 'R':
            # 执行替换
            if not config["target_path"]:
                print("\n[错误] 请先设置目标路径！")
                input_text("\n按回车继续...")
                continue

            print("")
            num = input_text("请输入要替换的角色编号: ").strip()
            try:
                idx = int(num) - 1
                roles = config.get("roles", [])
                if 0 <= idx < len(roles):
                    role_name = roles[idx]
                    print("\n即将用【%s】的文件覆盖目标路径: %s" % (role_name, config["target_path"]))
                    confirm = input_text("确认？(Y/N): ").strip().upper()
                    if confirm == 'Y':
                        success, msg = copy_role_files(role_name, config["target_path"])
                        print("\n" + msg)
                    else:
                        print("[取消]")
                else:
                    print("[错误] 编号无效")
            except ValueError:
                print("[错误] 请输入有效的数字")
            input_text("\n按回车继续...")

        elif choice == 'W':
            # 保存：将目标路径文件保存到角色文件夹
            if not config["target_path"]:
                print("\n[错误] 请先设置目标路径！")
                input_text("\n按回车继续...")
                continue

            print("")
            print("当前目标路径: %s" % config["target_path"])
            print("")
            print("已有角色: %s" % ", ".join(config["roles"]))
            print("")
            name = input_text("请输入保存的角色名称 (输入已有名称则覆盖): ").strip()
            if not name:
                print("[取消] 未输入名称")
                input_text("\n按回车继续...")
                continue

            # 如果角色已存在，提示确认覆盖
            if name in config["roles"]:
                confirm = input_text("角色【%s】已存在，确认覆盖？(Y/N): " % name).strip().upper()
                if confirm != 'Y':
                    print("[取消]")
                    input_text("\n按回车继续...")
                    continue

            success, msg = save_to_role(name, config["target_path"], config)
            print("\n" + msg)
            input_text("\n按回车继续...")

        elif choice == 'Q':
            print("\n再见！")
            break

        else:
            # 尝试直接输入数字快速替换
            try:
                idx = int(choice) - 1
                roles = config.get("roles", [])
                if 0 <= idx < len(roles):
                    if not config["target_path"]:
                        print("\n[错误] 请先设置目标路径！")
                        input_text("\n按回车继续...")
                        continue
                    role_name = roles[idx]
                    print("\n即将用【%s】的文件覆盖目标路径: %s" % (role_name, config["target_path"]))
                    confirm = input_text("确认？(Y/N): ").strip().upper()
                    if confirm == 'Y':
                        success, msg = copy_role_files(role_name, config["target_path"])
                        print("\n" + msg)
                    else:
                        print("[取消]")
                    input_text("\n按回车继续...")
                else:
                    pass
            except ValueError:
                pass


if __name__ == "__main__":
    main()
