import tkinter as tk
from tkinter import ttk, filedialog, simpledialog
from tkinter import simpledialog
from tkinter.messagebox import showinfo, askyesno
import threading
import json
from PIL import Image, ImageTk
import os
from image import get_date_taken, ask_question, process_image, read_and_print_data, write_to_excel, start_scan
import os

class App(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("Receipt Scanner")
        self.geometry("800x600")

        self.create_widgets()


    def set_personal(self):
        selected_item = self.tree.selection()[0]
        self.tree.set(selected_item, "Type", "Personal")

    def set_business(self):
        selected_item = self.tree.selection()[0]
        self.tree.set(selected_item, "Type", "Business")



    def create_widgets(self):
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(pady=10, expand=True, fill=tk.BOTH)

        self.create_scan_tab()
        self.create_verify_tab()

    def create_scan_tab(self):
        self.scan_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.scan_tab, text="Scan")
        pb = ttk.Progressbar(self.scan_tab, orient="horizontal", length=200, mode="indeterminate")
        self.scan_button = ttk.Button(self.scan_tab, text="Start Scan", command=lambda: [(self.start_scan_thread(pb=pb))])
        self.scan_button.pack(pady=20)
        pb.pack(pady=20)

    def create_verify_tab(self):
        self.verify_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.verify_tab, text="Verify")

        self.tree = ttk.Treeview(self.verify_tab, columns=("Company", "Total", "Date Taken", "Type"))

        self.tree.heading("#0", text="Image")
        self.tree.heading("Company", text="Company Name")
        self.tree.heading("Total", text="Total Price")
        self.tree.heading("Date Taken", text="Date Taken")
        self.tree.heading("Type", text="Type")
        self.tree.pack(expand=True, fill=tk.BOTH, side=tk.LEFT)

        self.tree.bind("<Double-1>", self.on_item_double_click)

        self.load_data_button = ttk.Button(self.verify_tab, text="Load Data", command=self.load_data)
        self.load_data_button.pack(pady=10)

        self.save_excel_button = ttk.Button(self.verify_tab, text="Save as Excel", command=lambda: write_to_excel(self.tree))

        self.save_excel_button.pack(pady=10)

        self.image_frame = ttk.Frame(self.verify_tab)
        self.image_frame.pack(pady=20)

        self.prev_button = ttk.Button(self.image_frame, text="Prev", command=self.show_prev_image)
        self.prev_button.grid(row=0, column=0)

        self.image_label = ttk.Label(self.image_frame)
        self.image_label.grid(row=0, column=1)

        self.next_button = ttk.Button(self.image_frame, text="Next", command=self.show_next_image)
        self.next_button.grid(row=0, column=2)

        self.image_directory = "images"
        self.image_files = sorted(os.listdir(self.image_directory))
        self.current_image_index = 0

        self.button_frame = ttk.Frame(self.verify_tab)
        self.button_frame.pack(side=tk.RIGHT, pady=20)

        self.personal_button = ttk.Button(self.button_frame, text="Personal", command=self.set_personal)
        self.personal_button.pack(pady=10)

        self.business_button = ttk.Button(self.button_frame, text="Business", command=self.set_business)
        self.business_button.pack(pady=10)


    def start_scan_thread(self, pb):
        thread = threading.Thread(target=start_scan)
        thread.start()
        thread.join()

        showinfo("Success", "Scan completed successfully!")
        pb.stop()

    def on_item_double_click(self, event):
        selected_item = self.tree.selection()[0]
        column = self.tree.identify_column(event.x)

        if column == "#0":
            self.show_image(self.tree.item(selected_item, "text"))
        else:
            values = self.tree.item(selected_item, "values")
            column_index = int(column[1]) - 1
            if column_index < len(values):
                value = values[column_index]
            else:
                return  # You may add some error message or warning here if necessary

            new_value = tk.simpledialog.askstring("Edit Value", f"Enter new value for {value}:")

            if new_value:
                self.tree.set(selected_item, column, new_value)
                self.update_json_data(selected_item, column, new_value)

    def update_json_data(self, item, column, value):
        image_name = self.tree.item(item, "text")
        with open("data.json", "r") as infile:
            data = json.load(infile)

        if column == "#1":
            data[image_name]["company"]["company name"] = f"<s_answer>{value}</s_answer>"
        elif column == "#2":
            data[image_name]["total"]["total price"] = f"<s_answer>{value}</s_answer>"

        with open("data.json", "w") as outfile:
            json.dump(data, outfile, indent=2)

    def load_data(self):
        # Clear existing data in the treeview
        for item in self.tree.get_children():
            self.tree.delete(item)

        with open("data.json", "r") as infile:
            data = json.load(infile)

        for image_name, image_data in data.items():
            company_name = image_data["company"]["company name"].split("</s_answer>")[0].split(">")[-1]
            total_price = image_data["total"]["total price"].split("</s_answer>")[0].split(">")[-1]
            date_taken = get_date_taken(os.path.join('images', image_name))

            self.tree.insert("", tk.END, text=image_name, values=(company_name, total_price, date_taken))

    def show_image(self, image_name):
        image_path = os.path.join(self.image_directory, image_name)
        image = Image.open(image_path)
        image.thumbnail((400, 400))
        photo = ImageTk.PhotoImage(image)

        self.image_label.config(image=photo)
        self.image_label.image = photo

        self.current_image_index = self.image_files.index(image_name)
        self.highlight_image_in_treeview(image_name)

    def highlight_image_in_treeview(self, image_name):
        for item in self.tree.get_children():
            if self.tree.item(item, "text") == image_name:
                self.tree.selection_set(item)
                break

    def show_next_image(self):
        if self.current_image_index < len(self.image_files) - 1:
            self.current_image_index += 1
            next_image_name = self.image_files[self.current_image_index]
            self.show_image(next_image_name)

    def show_prev_image(self):
        if self.current_image_index > 0:
            self.current_image_index -= 1
            prev_image_name = self.image_files[self.current_image_index]
            self.show_image(prev_image_name)

if __name__ == "__main__":
    app = App()
    app.mainloop()
