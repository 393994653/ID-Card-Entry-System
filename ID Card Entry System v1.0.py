import json
import os
import tkinter as tk
from tkinter import messagebox, simpledialog
from ttkbootstrap import Style, Label, Entry, Button, Frame


# 身份证校验码计算
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


# 加载行政区划数据（适配嵌套结构）
def load_area_codes():
    area_map = {}

    def process_node(node, parent_names=[]):
        code = str(node["code"])[:6]  # 截取前6位作为行政区代码
        current_name = node["name"]
        current_level = node["level"]

        # 处理直辖市特殊结构
        if current_level == 1 and current_name.endswith(("市", "省", "自治区")):
            parent_names = [current_name]

        if current_level == 3:  # 区县级
            full_name = parent_names[0]  # 省级名称
            if len(parent_names) > 1:
                full_name += parent_names[1]  # 市级名称
            full_name += current_name
            area_map[code] = full_name
        elif current_level == 2 and current_name != "市辖区":
            parent_names = parent_names.copy()
            parent_names.append(current_name)

        if "children" in node:
            for child in node["children"]:
                process_node(child, parent_names.copy())

    try:
        with open("config/area_code.json", "r", encoding="utf-8") as f:
            data = json.load(f)
            for province in data:
                process_node(province)
        return area_map
    except Exception as e:
        messagebox.showerror("错误", f"加载行政区划数据失败：{str(e)}")
        return {}


# 解析身份证信息
def parse_id_info(id_number, area_codes):
    area_code = id_number[:6]
    birth_date = f"{id_number[6:10]}-{id_number[10:12]}-{id_number[12:14]}"
    gender = "男" if int(id_number[16]) % 2 else "女"

    # 优化显示格式
    location = area_codes.get(area_code, "未知地区")
    location = location.replace("市辖区", "")  # 移除冗余信息

    return {"户籍地": location, "出生日期": birth_date, "性别": gender}


class SFZApp:
    def __init__(self, master):
        self.master = master
        self.master.title("身份证信息管理系统")
        self.master.geometry("680x450")

        self.style = Style(theme="minty")
        self.area_codes = load_area_codes()
        self.existing_records = self.load_records()

        self.create_widgets()

    def create_widgets(self):
        main_frame = Frame(self.master)
        main_frame.pack(pady=25, padx=25, fill="both", expand=True)

        # 输入区域
        input_frame = Frame(main_frame)
        input_frame.pack(fill="x")

        Label(input_frame, text="姓　　名：", font=("微软雅黑", 12)).pack(
            side="left", padx=5
        )

        self.name_entry = Entry(input_frame, width=25, font=("微软雅黑", 12))
        self.name_entry.pack(side="left", padx=5)
        
        self.name_entry.bind("<Return>", lambda event: self.search_record())
        
        Button(
            input_frame,
            text="查询/录入",
            command=self.search_record,
            bootstyle="primary",
        ).pack(side="left", padx=10)

        # 结果显示区域
        self.result_frame = Frame(main_frame)
        self.result_frame.pack(fill="both", expand=True, pady=15)

        # 底部信息
        Label(
            main_frame,
            text="提示：新录入身份证会自动验证有效性并解析信息",
            font=("微软雅黑", 9),
            bootstyle="secondary",
        ).pack(side="bottom")

    def load_records(self):
        records = {}
        if os.path.exists("config/database.sfz"):
            with open("config/database.sfz", "r", encoding="utf-8") as f:
                for line in f.readlines():
                    parts = line.strip().split(",")
                    if len(parts) >= 2:
                        records[parts[0]] = parts[1]
        return records

    def search_record(self):
        name = self.name_entry.get().strip()
        if not name:
            messagebox.showwarning("提示", "请输入姓名")
            return

        if name in self.existing_records:
            self.show_result(name, self.existing_records[name])
        else:
            self.add_new_record(name)

    def show_result(self, name, id_num):
        for widget in self.result_frame.winfo_children():
            widget.destroy()

        info = parse_id_info(id_num, self.area_codes)

        result_text = [
            f"姓　　名：{name}",
            f"身份证号：{id_num}",
            f"户 籍 地：{info['户籍地']}",
            f"出生日期：{info['出生日期']}",
            f"性　　别：{info['性别']}",
        ]

        for text in result_text:
            Label(self.result_frame, text=text, font=("微软雅黑", 12), anchor="w").pack(
                fill="x", pady=3
            )

    def add_new_record(self, name):
        id_num = simpledialog.askstring(
            "输入身份证号", "请输入18位身份证号：", parent=self.master
        )
        if not id_num:
            return

        # 验证身份证
        if len(id_num) != 18:
            messagebox.showerror("错误", "身份证号长度不正确")
            return

        if not validate_check_code(id_num):
            messagebox.showerror("错误", "身份证校验码不正确")
            return

        # 检查是否已存在
        existing_id = self.existing_records.get(name)
        if existing_id:
            if existing_id == id_num:
                messagebox.showinfo("提示", "记录已存在")
            else:
                messagebox.showwarning("冲突", "该姓名已存在不同身份证记录")
            return

        # 解析并保存
        area_code = id_num[:6]
        area_name = self.area_codes.get(area_code, "未知地区")

        with open("config/database.sfz", "a", encoding="utf-8") as f:
            f.write(f"{name},{id_num},{area_name}\n")

        self.existing_records[name] = id_num
        messagebox.showinfo("成功", "记录已保存")
        self.show_result(name, id_num)


if __name__ == "__main__":
    root = tk.Tk()
    app = SFZApp(root)
    root.mainloop()
