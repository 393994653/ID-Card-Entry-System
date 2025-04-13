import json
import os
import tkinter as tk
from tkinter import messagebox, simpledialog
from ttkbootstrap import Style, Label, Entry, Button, Frame


# 身份证校验码验证函数
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


# 行政区划数据加载（适配嵌套JSON结构）
def load_area_codes():
    area_map = {}

    def process_node(node, parent_names=[]):
        code = str(node["code"])[:6]  # 截取前6位
        current_name = node["name"]
        current_level = node["level"]

        # 处理直辖市结构
        if current_level == 1 and current_name.endswith(("市", "省", "自治区")):
            parent_names = [current_name]

        # 生成完整地址名称
        full_name = ""
        if parent_names:
            full_name = "".join(parent_names)
        full_name += current_name

        # 添加当前节点到映射表
        area_map[code] = full_name

        # 处理子节点
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


# 身份证信息解析（支持分级查询）
def parse_id_info(id_number, area_codes):
    code = id_number[:6]

    # 分级查询逻辑
    location = area_codes.get(code)
    if not location:  # 尝试前4位+00
        code_4 = id_number[:4] + "00"
        location = area_codes.get(code_4)
        if not location:  # 尝试前2位+0000
            code_2 = id_number[:2] + "0000"
            location = area_codes.get(code_2, "未知地区")

    # 优化显示格式
    location = location.replace("市辖区", "")

    birth_date = f"{id_number[6:10]}-{id_number[10:12]}-{id_number[12:14]}"
    gender = "男" if int(id_number[16]) % 2 else "女"

    return {"户籍地": location, "出生日期": birth_date, "性别": gender}


class SFZApp:
    def __init__(self, master):
        self.master = master
        self.master.title("身份证信息管理系统 v2.0")
        self.master.geometry("720x500")

        # 界面样式设置
        self.style = Style(theme="minty")
        self.style.configure("TLabel", font=("微软雅黑", 12))
        self.style.configure("TButton", font=("微软雅黑", 12))

        # 加载数据
        self.area_codes = load_area_codes()
        self.existing_records = self.load_records()

        # 创建界面组件
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
        self.name_entry.bind("<Return>", lambda e: self.search_record())  # 回车绑定

        Button(
            input_frame,
            text="查询/录入",
            command=self.search_record,
            bootstyle="primary-outline",
        ).pack(side="left", padx=10)

        # 结果显示区域
        self.result_frame = Frame(main_frame)
        self.result_frame.pack(fill="both", expand=True, pady=15)

        # 状态栏
        self.status_bar = Label(
            main_frame,
            text="就绪 | 记录总数：{}".format(len(self.existing_records)),
            bootstyle="secondary",
        )
        self.status_bar.pack(side="bottom", fill="x")

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
            messagebox.showwarning("输入错误", "请输入有效姓名")
            return

        if name in self.existing_records:
            self.show_result(name, self.existing_records[name])
        else:
            self.add_new_record(name)

    def show_result(self, name, id_num):
        # 清空现有结果
        for widget in self.result_frame.winfo_children():
            widget.destroy()

        info = parse_id_info(id_num, self.area_codes)

        # 显示结果组件
        result_items = [
            ("姓　　名：", name),
            ("身份证号：", id_num),
            ("户 籍 地：", info["户籍地"]),
            ("出生日期：", info["出生日期"]),
            ("性　　别：", info["性别"]),
        ]

        for label_text, value in result_items:
            row_frame = Frame(self.result_frame)
            row_frame.pack(fill="x", pady=3)

            Label(row_frame, text=label_text, width=10, bootstyle="primary").pack(
                side="left"
            )

            Label(row_frame, text=value, bootstyle="info").pack(side="left", padx=5)

        # 更新状态栏
        self.status_bar.config(
            text="就绪 | 记录总数：{}".format(len(self.existing_records))
        )

    def add_new_record(self, name):
        # 获取身份证号
        id_num = simpledialog.askstring(
            "身份证录入", "请输入18位身份证号：", parent=self.master
        )
        if not id_num:
            return

        # 验证身份证有效性
        error_msg = None
        if len(id_num) != 18:
            error_msg = "身份证号长度不正确"
        elif not id_num[:17].isdigit():
            error_msg = "前17位必须为数字"
        elif not validate_check_code(id_num):
            error_msg = "校验码不正确"

        if error_msg:
            messagebox.showerror("输入错误", error_msg)
            return

        # 检查姓名冲突
        existing_id = self.existing_records.get(name)
        if existing_id:
            if existing_id == id_num:
                messagebox.showinfo("提示", "记录已存在")
                self.show_result(name, id_num)
                return
            else:
                messagebox.showwarning("数据冲突", "该姓名已存在不同身份证记录")
                return

        # 解析地区信息
        area_code = id_num[:6]
        area_name = self.area_codes.get(area_code)
        if not area_name:  # 自动补充上级信息
            area_name = parse_id_info(id_num, self.area_codes)["户籍地"]

        # 保存记录
        with open("config/database.sfz", "a", encoding="utf-8") as f:
            f.write(f"{name},{id_num},{area_name}\n")

        self.existing_records[name] = id_num
        messagebox.showinfo("操作成功", "记录已保存")
        self.show_result(name, id_num)


if __name__ == "__main__":
    root = tk.Tk()
    app = SFZApp(root)
    root.mainloop()
