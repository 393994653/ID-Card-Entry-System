# ID_Manager_v4.0.py
import sys
import os
import json
import threading
import tkinter as tk
from tkinter import messagebox, simpledialog, filedialog
from ttkbootstrap import Style, Label, Entry, Button, Frame


def get_resource_path(relative_path):
    """获取资源的绝对路径（支持开发模式和打包模式）"""
    try:
        base_path = sys._MEIPASS  # PyInstaller创建的临时文件夹
    except AttributeError:
        base_path = os.path.abspath(".")

    # 如果目标路径不存在则自动创建（用于database.sfz）
    full_path = os.path.join(base_path, relative_path)
    dir_path = os.path.dirname(full_path)
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)

    return full_path


def validate_check_code(id_number):
    """验证身份证校验码"""
    if len(id_number) != 18:
        return False
    try:
        coeffs = [7, 9, 10, 5, 8, 4, 2, 1, 6, 3, 7, 9, 10, 5, 8, 4, 2]
        check_codes = "10X98765432"
        total = sum(int(a) * b for a, b in zip(id_number[:17], coeffs))
        return id_number[-1].upper() == check_codes[total % 11]
    except:
        return False


class AreaCodeLoader:
    """行政区划数据加载器"""

    @classmethod
    def load(cls):
        area_map = {}
        path = get_resource_path("config/area_code.json")

        def process_node(node, parent_names=[]):
            code = str(node["code"])[:6]
            current_name = node["name"]
            current_level = node["level"]

            if current_level == 1 and current_name.endswith(("市", "省", "自治区")):
                parent_names = [current_name]

            full_name = "".join(parent_names) + current_name
            area_map[code] = full_name.replace("市辖区", "")

            if "children" in node:
                new_parent = parent_names.copy()
                if current_level == 1:
                    new_parent = [current_name]
                elif current_level == 2 and current_name != "市辖区":
                    new_parent.append(current_name)
                for child in node["children"]:
                    process_node(child, new_parent)

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                for province in data:
                    process_node(province)
            return area_map
        except Exception as e:
            messagebox.showerror(
                "致命错误",
                f"无法加载行政区划数据：\n{str(e)}\n"
                f"请确认config/area_code.json存在且格式正确",
            )
            sys.exit(1)


def parse_id_info(id_number, area_codes):
    """解析身份证信息"""
    code = id_number[:6]
    location = area_codes.get(code)
    if not location:  # 分级查询
        code_4 = id_number[:4] + "00"
        location = area_codes.get(code_4)
        if not location:
            code_2 = id_number[:2] + "0000"
            location = area_codes.get(code_2, "未知地区")

    birth_date = f"{id_number[6:10]}-{id_number[10:12]}-{id_number[12:14]}"
    gender = "男" if int(id_number[16]) % 2 else "女"
    return {"户籍地": location, "出生日期": birth_date, "性别": gender}


class SFZApp:
    def __init__(self, master):
        self.master = master
        self.master.title("身份证信息管理系统 v4.0")
        self.master.geometry("820x580")

        # 初始化样式
        self.style = Style(theme="minty")
        self._configure_styles()

        # 加载数据
        self.area_codes = AreaCodeLoader.load()
        self.database_path = get_resource_path("config/database.sfz")
        self.existing_records = self._load_records()

        # 构建界面
        self._create_widgets()

    def _configure_styles(self):
        """配置界面样式"""
        self.style.configure("TLabel", font=("微软雅黑", 12))
        self.style.configure("TButton", font=("微软雅黑", 11))
        self.style.configure("status.TLabel", font=("微软雅黑", 10))

    def _create_widgets(self):
        """创建界面组件"""
        main_frame = Frame(self.master)
        main_frame.pack(pady=20, padx=20, fill="both", expand=True)

        # 输入区域
        input_frame = Frame(main_frame)
        input_frame.pack(fill="x", pady=10)

        Label(input_frame, text="姓　　名：").pack(side="left", padx=5)
        self.name_entry = Entry(input_frame, width=28)
        self.name_entry.pack(side="left", padx=5)
        self.name_entry.bind("<Return>", lambda e: self._search_record())

        # 按钮组
        btn_frame = Frame(input_frame)
        btn_frame.pack(side="left", padx=15)
        Button(
            btn_frame,
            text="查询/录入",
            command=self._search_record,
            bootstyle="primary",
        ).pack(side="left", padx=3)
        Button(
            btn_frame,
            text="批量导入",
            command=self._start_batch_import,
            bootstyle="success",
        ).pack(side="left", padx=3)

        # 结果显示
        self.result_frame = Frame(main_frame)
        self.result_frame.pack(fill="both", expand=True, pady=15)

        # 状态栏
        self.status_bar = Label(
            main_frame,
            text=f"就绪 | 记录总数：{len(self.existing_records)}",
            bootstyle="secondary",
        )
        self.status_bar.pack(side="bottom", fill="x")

    def _load_records(self):
        """加载已有记录"""
        records = {}
        if os.path.exists(self.database_path):
            try:
                with open(self.database_path, "r", encoding="utf-8") as f:
                    for line in f:
                        parts = line.strip().split(",", 2)
                        if len(parts) >= 2:
                            records[parts[0]] = parts[1]
            except Exception as e:
                messagebox.showerror(
                    "数据错误",
                    f"无法读取数据库文件：\n{str(e)}\n"
                    "请检查config/database.sfz文件格式",
                )
        return records

    def _search_record(self):
        """处理查询/录入"""
        name = self.name_entry.get().strip()
        if not name:
            messagebox.showwarning("输入错误", "请输入有效姓名")
            return

        if name in self.existing_records:
            self._show_result(name, self.existing_records[name])
        else:
            self._add_new_record(name)

    def _show_result(self, name, id_num):
        """显示查询结果"""
        for widget in self.result_frame.winfo_children():
            widget.destroy()

        info = parse_id_info(id_num, self.area_codes)
        labels = [
            ("姓　　名：", name),
            ("身份证号：", id_num),
            ("户 籍 地：", info["户籍地"]),
            ("出生日期：", info["出生日期"]),
            ("性　　别：", info["性别"]),
        ]

        for text, value in labels:
            row = Frame(self.result_frame)
            row.pack(fill="x", pady=4)
            Label(row, text=text, width=10, bootstyle="primary").pack(side="left")
            Label(row, text=value, bootstyle="info").pack(side="left", padx=5)

        self.status_bar.config(text=f"就绪 | 记录总数：{len(self.existing_records)}")

    def _add_new_record(self, name):
        """添加新记录"""
        id_num = simpledialog.askstring(
            "输入身份证号", "请输入18位身份证号：", parent=self.master
        )
        if not id_num:
            return

        # 验证身份证
        error = None
        if len(id_num) != 18:
            error = "身份证号长度不正确"
        elif not id_num[:17].isdigit():
            error = "前17位必须为数字"
        elif not validate_check_code(id_num):
            error = "校验码不正确"

        if error:
            messagebox.showerror("输入错误", error)
            return

        # 检查重复
        if name in self.existing_records:
            if self.existing_records[name] == id_num:
                messagebox.showinfo("提示", "记录已存在")
                self._show_result(name, id_num)
                return
            else:
                messagebox.showwarning("冲突", "该姓名已存在不同身份证")
                return

        # 保存记录
        area = parse_id_info(id_num, self.area_codes)["户籍地"]
        try:
            with open(self.database_path, "a", encoding="utf-8") as f:
                f.write(f"{name},{id_num},{area}\n")
            self.existing_records[name] = id_num
            messagebox.showinfo("成功", "记录已保存")
            self._show_result(name, id_num)
        except Exception as e:
            messagebox.showerror("保存失败", f"无法写入数据库：\n{str(e)}")

    def _start_batch_import(self):
        """启动批量导入"""
        filetypes = [("支持的文件", "*.txt *.csv *.sfzx"), ("所有文件", "*.*")]
        path = filedialog.askopenfilename(title="选择导入文件", filetypes=filetypes)
        if path:
            threading.Thread(
                target=self._batch_import, args=(path,), daemon=True
            ).start()

    def _batch_import(self, filepath):
        """执行批量导入"""
        success = failed = 0
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                lines = f.readlines()

            for line in lines:
                line = line.strip()
                if not line:
                    continue

                parts = line.split()
                if len(parts) < 2:
                    failed += 1
                    continue

                id_num, name = parts[0], " ".join(parts[1:])
                if not validate_check_code(id_num):
                    failed += 1
                    continue

                # 检查记录
                if name in self.existing_records:
                    if self.existing_records[name] == id_num:
                        continue
                    else:
                        failed += 1
                        continue

                # 保存记录
                area = parse_id_info(id_num, self.area_codes)["户籍地"]
                with open(self.database_path, "a", encoding="utf-8") as f:
                    f.write(f"{name},{id_num},{area}\n")
                self.existing_records[name] = id_num
                success += 1

                # 更新状态
                self.master.after(
                    10,
                    lambda s=success, f=failed: self.status_bar.config(
                        text=f"导入中... 成功：{s} 失败：{f} 总数：{s+f}"
                    ),
                )

            # 完成提示
            self.master.after(
                0,
                lambda: messagebox.showinfo(
                    "导入完成", f"成功导入 {success} 条记录\n失败 {failed} 条"
                ),
            )
            self.master.after(
                0,
                lambda: self.status_bar.config(
                    text=f"就绪 | 记录总数：{len(self.existing_records)}"
                ),
            )

        except UnicodeDecodeError:
            self.master.after(
                0,
                lambda: messagebox.showerror(
                    "编码错误", "文件编码不是UTF-8，请用记事本另存为UTF-8格式"
                ),
            )
        except FileNotFoundError:
            self.master.after(
                0, lambda: messagebox.showerror("文件错误", "选择的文件不存在")
            )
        except Exception as e:
            error = str(e)
            self.master.after(
                0,
                lambda msg=error: messagebox.showerror(
                    "导入错误", f"文件处理失败：{msg}"
                ),
            )


if __name__ == "__main__":
    root = tk.Tk()
    app = SFZApp(root)
    root.mainloop()
