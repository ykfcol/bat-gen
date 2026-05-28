# -*- coding: utf-8 -*-
"""
角色文件替换工具（GUI版）
功能：管理角色集合，一键将角色文件夹内容覆盖到用户指定的目标路径
需要 Python 3.6+ 且安装了 tkinter
"""

import os
import sys
import json
import shutil
import hashlib
import hmac
import base64
import struct
import datetime
import uuid
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import logging

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s][%(funcName)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

# ========== 序列号验证密钥（必须和 keygen.py 一致） ==========
SECRET_KEY = "YourSuperSecretKey_ChangeThis_2024"
# ==============================================================

# 默认角色集合
DEFAULT_ROLES = [
    "孔雀", "白骨", "罗刹", "夜叉", "牛魔王", "百花羞",
    "百年猪妖", "羊头怪", "狮子", "虫子", "刑天", "刺猬", "猪", "熊"
]

CONFIG_FILE = "config.json"
LICENSE_FILE = "license.dat"


def get_base_path():
    """获取程序运行的基础路径（兼容打包后的exe）"""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def get_machine_id():
    """获取机器唯一标识"""
    # 使用多个硬件信息组合生成机器码
    raw = ""
    try:
        # Windows: 使用主板序列号
        if os.name == 'nt':
            import subprocess
            result = subprocess.run(
                ['wmic', 'baseboard', 'get', 'serialnumber'],
                capture_output=True, text=True, timeout=5
            )
            raw = result.stdout.strip()
        else:
            # Mac/Linux: 使用 uuid
            raw = str(uuid.getnode())
    except Exception:
        raw = str(uuid.getnode())

    # 生成短机器码（8位）
    machine_hash = hashlib.md5(raw.encode('utf-8')).hexdigest()[:8].upper()
    return machine_hash


def verify_serial(serial_str, machine_id=None):
    """
    验证序列号
    :param serial_str: 用户输入的序列号
    :param machine_id: 当前机器码
    :return: (valid, expire_date_str, error_msg)
    """
    try:
        # 去掉横杠和空格
        clean = serial_str.replace('-', '').replace(' ', '').strip().upper()

        # 补齐Base32填充
        padding = (8 - len(clean) % 8) % 8
        clean += '=' * padding

        # Base32解码
        raw = base64.b32decode(clean)

        if len(raw) != 12:
            return False, "", "序列号格式无效"

        # 拆分: data(6字节) + signature(6字节)
        data = raw[:6]
        signature = raw[6:]

        # 验证签名
        expected_sig = hmac.new(
            SECRET_KEY.encode('utf-8'),
            data,
            hashlib.sha256
        ).digest()[:6]

        if not hmac.compare_digest(signature, expected_sig):
            return False, "", "序列号无效"

        # 解析数据
        expire_days = struct.unpack('>H', data[:2])[0]
        machine_hash_in_serial = data[2:6]

        # 计算过期日期
        base_date = datetime.date(2024, 1, 1)
        expire_date = base_date + datetime.timedelta(days=expire_days)
        expire_str = expire_date.strftime('%Y-%m-%d')

        # 检查是否过期
        today = datetime.date.today()
        if today > expire_date:
            return False, expire_str, "序列号已过期（%s）" % expire_str

        # 检查机器绑定
        any_machine_hash = hashlib.md5("ANY".encode('utf-8')).digest()[:4]
        if machine_hash_in_serial != any_machine_hash:
            # 序列号绑定了特定机器
            if machine_id:
                current_machine_hash = hashlib.md5(machine_id.encode('utf-8')).digest()[:4]
                if machine_hash_in_serial != current_machine_hash:
                    return False, expire_str, "序列号与本机不匹配"

        return True, expire_str, ""

    except Exception as e:
        return False, "", "验证失败: " + str(e)


def load_license():
    """加载本地保存的序列号"""
    license_path = os.path.join(get_base_path(), LICENSE_FILE)
    try:
        if os.path.exists(license_path):
            with open(license_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get("serial", "")
    except Exception:
        pass
    return ""


def save_license(serial):
    """保存序列号到本地"""
    license_path = os.path.join(get_base_path(), LICENSE_FILE)
    try:
        with open(license_path, 'w', encoding='utf-8') as f:
            json.dump({"serial": serial}, f)
    except Exception as e:
        logger.error("保存序列号失败 error=%s", str(e))


def load_config():
    """加载配置文件"""
    config_path = os.path.join(get_base_path(), CONFIG_FILE)
    logger.info("加载配置文件 path=%s", config_path)
    try:
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                logger.info("配置加载成功 roles数量=%d", len(config.get('roles', [])))
                return config
    except Exception as e:
        logger.error("配置加载失败 error=%s", str(e))

    return {
        "collection_name": "野外+超级集合",
        "roles": DEFAULT_ROLES[:],
        "target_path": ""
    }


def save_config(config):
    """保存配置文件"""
    config_path = os.path.join(get_base_path(), CONFIG_FILE)
    logger.info("保存配置 path=%s roles数量=%d", config_path, len(config.get('roles', [])))
    try:
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        logger.info("配置保存成功")
    except Exception as e:
        logger.error("配置保存失败 error=%s", str(e))


def copy_role_files(role_name, target_path):
    """
    将角色文件夹的内容覆盖复制到目标路径
    :param role_name: 角色名称
    :param target_path: 目标路径
    :return: (success, message)
    """
    base_path = get_base_path()
    role_dir = os.path.join(base_path, role_name)
    logger.info("开始复制 role=%s source=%s target=%s", role_name, role_dir, target_path)

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
                logger.info("复制文件 %s", item)
            elif os.path.isdir(src):
                if os.path.exists(dst):
                    shutil.rmtree(dst)
                shutil.copytree(src, dst)
                copied_count += 1
                logger.info("复制目录 %s", item)

        msg = "[%s] 替换完成，共复制 %d 个项目" % (role_name, copied_count)
        logger.info(msg)
        return True, msg

    except Exception as e:
        msg = "复制失败: " + str(e)
        logger.error(msg)
        return False, msg


def save_to_role(role_name, target_path, config):
    """
    将目标路径的文件保存到角色文件夹（反向操作）
    如果角色文件夹已存在则清空后覆盖
    如果角色不在列表中则自动添加
    :param role_name: 角色名称
    :param target_path: 目标路径（源）
    :param config: 配置字典
    :return: (success, message)
    """
    base_path = get_base_path()
    role_dir = os.path.join(base_path, role_name)
    logger.info("保存到角色 role=%s source=%s target=%s", role_name, target_path, role_dir)

    if not os.path.exists(target_path):
        return False, "目标路径不存在: " + target_path

    items = os.listdir(target_path)
    if not items:
        return False, "目标路径为空，没有可保存的文件"

    try:
        # 如果角色文件夹已存在，清空它
        if os.path.exists(role_dir):
            shutil.rmtree(role_dir)

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
        logger.info(msg)
        return True, msg

    except Exception as e:
        msg = "保存失败: " + str(e)
        logger.error(msg)
        return False, msg


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

    logger.info("一键生成 roles数量=%d target=%s", len(roles), target_path)

    if not target_path:
        return False, "请先设置目标路径！"

    results = []
    for role in roles:
        role_dir = os.path.join(base_path, role)
        if not os.path.exists(role_dir):
            os.makedirs(role_dir)
            logger.info("创建文件夹 %s", role_dir)

        bat_content = generate_bat(role, target_path)
        bat_path = os.path.join(base_path, role + ".bat")
        with open(bat_path, 'w', encoding='utf-8') as f:
            f.write(bat_content)
        results.append("OK " + role)

    msg = "生成完成！共 %d 个角色:\n" % len(roles) + "\n".join(results)
    logger.info("一键生成完成 总数=%d", len(roles))
    return True, msg


class LicenseDialog:
    """序列号验证窗口"""

    def __init__(self):
        self.result = False
        self.root = tk.Tk()
        self.root.title("激活 - 角色文件替换工具")
        self.root.geometry("450x280")
        self.root.resizable(False, False)
        self._build_ui()

    def _build_ui(self):
        """构建激活界面"""
        ttk.Label(self.root, text="角色文件替换工具", font=("", 16, "bold")).pack(pady=10)
        ttk.Label(self.root, text="请输入序列号激活软件").pack(pady=5)

        # 机器码显示
        machine_id = get_machine_id()
        machine_frame = ttk.Frame(self.root)
        machine_frame.pack(pady=5)
        ttk.Label(machine_frame, text="本机机器码:").pack(side=tk.LEFT)
        machine_entry = ttk.Entry(machine_frame, width=12)
        machine_entry.insert(0, machine_id)
        machine_entry.configure(state='readonly')
        machine_entry.pack(side=tk.LEFT, padx=5)

        # 序列号输入
        ttk.Label(self.root, text="序列号:").pack(pady=5)
        self.serial_var = tk.StringVar()

        # 尝试加载已保存的序列号
        saved_serial = load_license()
        if saved_serial:
            self.serial_var.set(saved_serial)

        serial_entry = ttk.Entry(self.root, textvariable=self.serial_var, width=40, font=("Courier", 12))
        serial_entry.pack(pady=5)
        serial_entry.focus()

        # 状态提示
        self.status_var = tk.StringVar()
        self.status_label = ttk.Label(self.root, textvariable=self.status_var, foreground="red")
        self.status_label.pack(pady=5)

        # 按钮
        btn_frame = ttk.Frame(self.root)
        btn_frame.pack(pady=10)
        ttk.Button(btn_frame, text="激活", command=self._activate).pack(side=tk.LEFT, padx=10)
        ttk.Button(btn_frame, text="退出", command=self._quit).pack(side=tk.LEFT, padx=10)

        self.root.bind('<Return>', lambda e: self._activate())

        # 如果有已保存的序列号，自动验证
        if saved_serial:
            self._activate()

    def _activate(self):
        """验证序列号"""
        serial = self.serial_var.get().strip()
        if not serial:
            self.status_var.set("请输入序列号")
            return

        machine_id = get_machine_id()
        valid, expire_str, error = verify_serial(serial, machine_id)

        if valid:
            # 保存序列号
            save_license(serial)
            self.result = True
            self.root.destroy()
        else:
            self.status_var.set(error if error else "序列号无效")
            self.status_label.configure(foreground="red")

    def _quit(self):
        """退出"""
        self.root.destroy()

    def run(self):
        """运行激活窗口"""
        self.root.mainloop()
        return self.result


class App:
    """主界面"""

    def __init__(self):
        self.config = load_config()
        self.root = tk.Tk()
        self.root.title("角色文件替换工具 - " + self.config['collection_name'])
        self.root.geometry("750x620")
        self.root.resizable(True, True)
        self._build_ui()
        logger.info("界面初始化完成")

    def _build_ui(self):
        """构建界面"""
        # === 目标路径区域 ===
        path_frame = ttk.LabelFrame(self.root, text="目标路径设置", padding=10)
        path_frame.pack(fill=tk.X, padx=10, pady=5)

        self.path_var = tk.StringVar(value=self.config.get("target_path", ""))
        ttk.Entry(path_frame, textvariable=self.path_var, width=50).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(path_frame, text="浏览...", command=self._browse_path).pack(side=tk.LEFT, padx=5)
        ttk.Button(path_frame, text="保存路径", command=self._save_path).pack(side=tk.LEFT)

        # === 操作按钮区域 ===
        action_frame = ttk.LabelFrame(self.root, text="操作", padding=10)
        action_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Button(action_frame, text="一键生成所有BAT和文件夹", command=self._generate_all).pack(side=tk.LEFT, padx=5)
        ttk.Button(action_frame, text="添加角色", command=self._add_role).pack(side=tk.LEFT, padx=5)
        ttk.Button(action_frame, text="删除角色", command=self._delete_role).pack(side=tk.LEFT, padx=5)
        ttk.Button(action_frame, text="保存到角色", command=self._save_to_role).pack(side=tk.LEFT, padx=5)

        # === 角色列表区域 ===
        roles_frame = ttk.LabelFrame(self.root, text="角色集合: " + self.config['collection_name'] + " (点击按钮=替换到目标路径)", padding=10)
        roles_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # 滚动区域
        canvas = tk.Canvas(roles_frame)
        scrollbar = ttk.Scrollbar(roles_frame, orient="vertical", command=canvas.yview)
        self.roles_inner_frame = ttk.Frame(canvas)

        self.roles_inner_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=self.roles_inner_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self._refresh_role_buttons()

        # === 状态栏 ===
        self.status_var = tk.StringVar(value="就绪")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(fill=tk.X, side=tk.BOTTOM, padx=10, pady=5)

    def _refresh_role_buttons(self):
        """刷新角色按钮网格"""
        for widget in self.roles_inner_frame.winfo_children():
            widget.destroy()

        roles = self.config.get("roles", [])
        columns = 4

        for i, role in enumerate(roles):
            row = i // columns
            col = i % columns
            btn = ttk.Button(
                self.roles_inner_frame,
                text=role,
                command=lambda r=role: self._apply_role(r)
            )
            btn.grid(row=row, column=col, padx=5, pady=5, sticky="ew")

        for col_idx in range(columns):
            self.roles_inner_frame.columnconfigure(col_idx, weight=1)

    def _browse_path(self):
        """浏览选择目标路径"""
        path = filedialog.askdirectory(title="选择目标路径")
        if path:
            self.path_var.set(path)
            logger.info("用户选择路径 path=%s", path)

    def _save_path(self):
        """保存目标路径到配置"""
        path = self.path_var.get().strip()
        if not path:
            messagebox.showwarning("提示", "请先选择或输入目标路径！")
            return
        self.config["target_path"] = path
        save_config(self.config)
        self.status_var.set("目标路径已保存: " + path)
        messagebox.showinfo("成功", "目标路径已保存！")

    def _generate_all(self):
        """一键生成所有bat和文件夹"""
        path = self.path_var.get().strip()
        if not path:
            messagebox.showwarning("提示", "请先设置目标路径！")
            return

        self.config["target_path"] = path
        save_config(self.config)

        success, msg = generate_all(self.config)
        if success:
            self.status_var.set("一键生成完成")
            messagebox.showinfo("生成完成", msg)
        else:
            self.status_var.set("生成失败")
            messagebox.showerror("错误", msg)

    def _add_role(self):
        """添加新角色"""
        dialog = tk.Toplevel(self.root)
        dialog.title("添加角色")
        dialog.geometry("300x120")
        dialog.transient(self.root)
        dialog.grab_set()

        ttk.Label(dialog, text="角色名称:").pack(pady=5)
        name_var = tk.StringVar()
        entry = ttk.Entry(dialog, textvariable=name_var, width=30)
        entry.pack(pady=5)
        entry.focus()

        def confirm():
            name = name_var.get().strip()
            if not name:
                messagebox.showwarning("提示", "请输入角色名称！", parent=dialog)
                return
            if name in self.config["roles"]:
                messagebox.showwarning("提示", "角色 [%s] 已存在！" % name, parent=dialog)
                return

            self.config["roles"].append(name)
            save_config(self.config)
            self._refresh_role_buttons()
            self.status_var.set("已添加角色: " + name)
            logger.info("添加角色 name=%s", name)
            dialog.destroy()

        ttk.Button(dialog, text="确定", command=confirm).pack(pady=10)
        dialog.bind('<Return>', lambda e: confirm())

    def _delete_role(self):
        """删除角色（弹出选择框）"""
        roles = self.config.get("roles", [])
        if not roles:
            messagebox.showinfo("提示", "没有可删除的角色")
            return

        dialog = tk.Toplevel(self.root)
        dialog.title("删除角色")
        dialog.geometry("300x350")
        dialog.transient(self.root)
        dialog.grab_set()

        ttk.Label(dialog, text="选择要删除的角色（可多选）:").pack(pady=5)

        listbox = tk.Listbox(dialog, selectmode=tk.MULTIPLE, height=12)
        listbox.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        for role in roles:
            listbox.insert(tk.END, role)

        def confirm():
            selected = listbox.curselection()
            if not selected:
                messagebox.showwarning("提示", "请选择要删除的角色！", parent=dialog)
                return

            names = [roles[i] for i in selected]
            if messagebox.askyesno("确认", "确定删除以下角色？\n" + ", ".join(names), parent=dialog):
                for name in names:
                    self.config["roles"].remove(name)
                    logger.info("删除角色 name=%s", name)
                save_config(self.config)
                self._refresh_role_buttons()
                self.status_var.set("已删除 %d 个角色" % len(names))
                dialog.destroy()

        ttk.Button(dialog, text="删除选中", command=confirm).pack(pady=10)

    def _save_to_role(self):
        """保存：将目标路径文件保存到角色文件夹"""
        target_path = self.path_var.get().strip()
        if not target_path:
            messagebox.showwarning("提示", "请先设置目标路径！")
            return

        dialog = tk.Toplevel(self.root)
        dialog.title("保存到角色")
        dialog.geometry("350x180")
        dialog.transient(self.root)
        dialog.grab_set()

        ttk.Label(dialog, text="将目标路径的文件保存到角色文件夹").pack(pady=5)
        ttk.Label(dialog, text="源: " + target_path, wraplength=320).pack(pady=2)
        ttk.Label(dialog, text="输入角色名称 (已有则覆盖):").pack(pady=5)

        name_var = tk.StringVar()
        entry = ttk.Entry(dialog, textvariable=name_var, width=30)
        entry.pack(pady=5)
        entry.focus()

        def confirm():
            name = name_var.get().strip()
            if not name:
                messagebox.showwarning("提示", "请输入角色名称！", parent=dialog)
                return

            # 如果角色已存在，确认覆盖
            if name in self.config["roles"]:
                if not messagebox.askyesno("确认", "角色【%s】已存在，确认覆盖？" % name, parent=dialog):
                    return

            success, msg = save_to_role(name, target_path, self.config)
            if success:
                self._refresh_role_buttons()
                self.status_var.set(msg)
                messagebox.showinfo("完成", msg, parent=dialog)
                dialog.destroy()
            else:
                messagebox.showerror("错误", msg, parent=dialog)

        ttk.Button(dialog, text="保存", command=confirm).pack(pady=10)
        dialog.bind('<Return>', lambda e: confirm())

    def _apply_role(self, role_name):
        """点击角色按钮，执行文件替换"""
        target_path = self.path_var.get().strip()
        if not target_path:
            messagebox.showwarning("提示", "请先设置目标路径！")
            return

        if not messagebox.askyesno("确认", "确定将【%s】的文件覆盖到目标路径？\n%s" % (role_name, target_path)):
            return

        self.status_var.set("正在替换: %s..." % role_name)
        self.root.update()

        success, msg = copy_role_files(role_name, target_path)
        if success:
            self.status_var.set(msg)
            messagebox.showinfo("完成", msg)
        else:
            self.status_var.set("替换失败")
            messagebox.showerror("错误", msg)

    def run(self):
        """启动主循环"""
        self.root.mainloop()


if __name__ == "__main__":
    logger.info("程序启动")

    # 先检查序列号
    saved_serial = load_license()
    machine_id = get_machine_id()

    need_activate = True
    if saved_serial:
        valid, expire_str, error = verify_serial(saved_serial, machine_id)
        if valid:
            need_activate = False
            logger.info("序列号验证通过 expire=%s", expire_str)

    if need_activate:
        # 弹出激活窗口
        license_dialog = LicenseDialog()
        if not license_dialog.run():
            logger.info("用户未激活，退出")
            sys.exit(0)

    # 启动主程序
    app = App()
    app.run()
