import json
import os
import threading
import tkinter as tk
from tkinter import messagebox, simpledialog, filedialog
from ttkbootstrap import Style, Label, Entry, Button, Frame


def validate_check_code(id_number):
    if len(id_number) != 18:
        return False
    try:
        coeffs = [7, 9, 10, 5, 8, 4, 2, 1, 6, 3, 7, 9, 10, 5, 8, 4, 2]
        check_codes = "10X98765432"
        total = sum(int(a) * b for a, b in zip(id_number[:17], coeffs))
        return id_number[-1].upper() == check_codes[total % 11]
    except:
        return False


def load_area_codes():
    area_map = {}

    def process_node(node, parent_names=[]):
        code = str(node["code"])[:6]
        current_name = node["name"]
        current_level = node["level"]

        if current_level == 1 and current_name.endswith(("市", "省", "自治区")):
            parent_names = [current_name]

        full_name = ""
        if parent_names:
            full_name = "".join(parent_names)
        full_name += current_name

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
        with open("config/area_code.json", "r", encoding="utf-8") as f:
            data = json.load(f)
            for province in data:
                process_node(province)
        return area_map
    except Exception as e:
        messagebox.showerror("错误", f"行政区划数据加载失败：{str(e)}")
        return {}


def parse_id_info(id_number, area_codes):
    code = id_number[:6]
    location = area_codes.get(code)
    if not location:
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
        self.master.title("身份证信息管理系统 v3.0")
        self.master.geometry("800x550")

        self.style = Style(theme="minty")
        self.style.configure("TLabel", font=("微软雅黑", 12))
        self.style.configure("TButton", font=("微软雅黑", 12))

        self.area_codes = load_area_codes()
        self.existing_records = self.load_records()

        self.create_widgets()

    def create_widgets(self):
        main_frame = Frame(self.master)
        main_frame.pack(pady=25, padx=25, fill="both", expand=True)

        # 输入区域
        input_frame = Frame(main_frame)
        input_frame.pack(fill="x", pady=10)

        Label(input_frame, text="姓　　名：").pack(side="left", padx=5)
        self.name_entry = Entry(input_frame, width=25)
        self.name_entry.pack(side="left", padx=5)
        self.name_entry.bind("<Return>", lambda e: self.search_record())

        btn_frame = Frame(input_frame)
        btn_frame.pack(side="left", padx=10)
        Button(
            btn_frame,
            text="查询/录入",
            command=self.search_record,
            bootstyle="primary-outline",
        ).pack(side="left", padx=3)
        Button(
            btn_frame,
            text="批量导入",
            command=self.start_batch_import,
            bootstyle="success-outline",
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

    def load_records(self):
        records = {}
        if os.path.exists("config/database.sfz"):
            with open("config/database.sfz", "r", encoding="utf-8") as f:
                for line in f:
                    parts = line.strip().split(",", 2)
                    if len(parts) >= 2:
                        records[parts[0]] = parts[1]
        return records

    def search_record(self):
        name = self.name_entry.get().strip()
        if not name:
            messagebox.showwarning("输入错误", "请输入有效姓名")
            return
        if name in self.existing_records:
            self.show_result(name, self.existing_records[name])
        else:
            self.add_new_record(name)

    def show_result(self, name, id_num):
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
            row.pack(fill="x", pady=3)
            Label(row, text=text, width=10, bootstyle="primary").pack(side="left")
            Label(row, text=value, bootstyle="info").pack(side="left", padx=5)
        self.status_bar.config(text=f"就绪 | 记录总数：{len(self.existing_records)}")

    def add_new_record(self, name):
        id_num = simpledialog.askstring(
            "输入身份证号", "请输入18位身份证号：", parent=self.master
        )
        if not id_num:
            return

        if len(id_num) != 18 or not id_num[:17].isdigit():
            messagebox.showerror("错误", "身份证格式错误")
            return
        if not validate_check_code(id_num):
            messagebox.showerror("错误", "校验码不正确")
            return

        if name in self.existing_records:
            if self.existing_records[name] == id_num:
                messagebox.showinfo("提示", "记录已存在")
            else:
                messagebox.showwarning("冲突", "该姓名已存在不同身份证")
            return

        area_name = parse_id_info(id_num, self.area_codes)["户籍地"]
        with open("config/database.sfz", "a", encoding="utf-8") as f:
            f.write(f"{name},{id_num},{area_name}\n")
        self.existing_records[name] = id_num
        messagebox.showinfo("成功", "记录已保存")
        self.show_result(name, id_num)

    def start_batch_import(self):
        filetypes = [("支持的文件", "*.txt *.sfzx"), ("所有文件", "*.*")]
        path = filedialog.askopenfilename(title="选择导入文件", filetypes=filetypes)
        if path:
            threading.Thread(
                target=self.batch_import, args=(path,), daemon=True
            ).start()

    def batch_import(self, filepath):
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
                if len(id_num) != 18 or not validate_check_code(id_num):
                    failed += 1
                    continue

                if name in self.existing_records:
                    if self.existing_records[name] == id_num:
                        continue
                    else:
                        failed += 1
                        continue

                area = parse_id_info(id_num, self.area_codes)["户籍地"]
                with open("config/database.sfz", "a", encoding="utf-8") as f:
                    f.write(f"{name},{id_num},{area}\n")
                self.existing_records[name] = id_num
                success += 1

                self.master.after(
                    10,
                    lambda: self.status_bar.config(
                        text=f"导入中... 成功：{success} 失败：{failed} 总数：{success+failed}"
                    ),
                )

            self.master.after(
                0,
                lambda: messagebox.showinfo(
                    "导入完成", f"成功导入 {success} 条，失败 {failed} 条"
                ),
            )
            self.master.after(
                0,
                lambda: self.status_bar.config(
                    text=f"就绪 | 记录总数：{len(self.existing_records)}"
                ),
            )

        except Exception as e:
            self.master.after(
                0, lambda: messagebox.showerror("导入错误", f"文件读取失败：{str(e)}")
            )


if __name__ == "__main__":
    root = tk.Tk()
    app = SFZApp(root)
    root.mainloop()
