import re
import os
from transformers import DonutProcessor, VisionEncoderDecoderModel
import torch
from PIL import Image
import json
import openpyxl
import sys
processor = DonutProcessor.from_pretrained("naver-clova-ix/donut-base-finetuned-docvqa")
model = VisionEncoderDecoderModel.from_pretrained("naver-clova-ix/donut-base-finetuned-docvqa")
device = "cuda" if torch.cuda.is_available() else "cpu"
model = model.to('cuda')
image_directory = "images"


from PIL import Image
from PIL.ExifTags import TAGS

def get_date_taken(file_path):
    try:
        with Image.open(file_path) as img:
            exif_data = img._getexif()
            if exif_data is not None:
                for tag_id, value in exif_data.items():
                    tag = TAGS.get(tag_id, tag_id)
                    if tag == 'DateTimeOriginal':
                        return value
    except Exception as e:
        print(f"Error: {e}")
    return None


def ask_question(question):
    task_prompt = "<s_docvqa><s_question>{user_input}</s_question><s_answer>"
    prompt = task_prompt.replace("{user_input}", question)
    decoder_input_ids = processor.tokenizer(prompt, add_special_tokens=False, return_tensors="pt").input_ids

    return decoder_input_ids

def process_image(image_path):
    image = Image.open(image_path)
    pixel_values = processor(image, return_tensors="pt").pixel_values.to(device)

    return pixel_values

def read_and_print_data():
    with open("data.json", "r") as infile:
        data = json.load(infile)

    print("Data from JSON file:")
    print(json.dumps(data, indent=2))

def write_to_excel(treeview):
    import xlsxwriter
    import os

    # Create a new Excel workbook and add a worksheet
    workbook = xlsxwriter.Workbook('receipts.xlsx')
    worksheet = workbook.add_worksheet()

    # Write the header row
    headers = ['Image', 'Company Name', 'Total Price', 'Date Taken', 'Type']
    for col, header in enumerate(headers):
        worksheet.write(0, col, header)

    # Write the data from the treeview
    for row, item_id in enumerate(treeview.get_children(), start=1):
        image_name = treeview.item(item_id, "text")
        values = treeview.item(item_id, "values")
        worksheet.write(row, 0, image_name)
        for col, value in enumerate(values, start=1):
            worksheet.write(row, col, value)

    # Close the Excel workbook
    workbook.close()

    print("Excel file created: receipts.xlsx")


def start_scan():
    data = {}
    
    for filename in os.listdir(image_directory):
        image_path = os.path.join(image_directory, filename)

        pixel_values = process_image(image_path)

        question1 = "What's the name of the company?"
        decoder_input_ids1 = ask_question(question1)

        question2 = "What's the total price?"
        decoder_input_ids2 = ask_question(question2)

        for question, decoder_input_ids in zip([question1, question2], [decoder_input_ids1, decoder_input_ids2]):
            outputs = model.generate(
                pixel_values.to(device),
                decoder_input_ids=decoder_input_ids.to(device),
                max_length=512,
                early_stopping=True,
                pad_token_id=processor.tokenizer.pad_token_id,
                eos_token_id=processor.tokenizer.eos_token_id,
                use_cache=True,
                num_beams=1,
                bad_words_ids=[[processor.tokenizer.unk_token_id]],
                return_dict_in_generate=True,
            )

            sequence = processor.batch_decode(outputs.sequences)[0]
            sequence = sequence.replace(processor.tokenizer.eos_token, "").replace(processor.tokenizer.pad_token, "")
            sequence = re.sub(r"<.*?>", "", sequence, count=1).strip()  # remove first task start token

            if question == question1:
                company_name = sequence
            else:
                total_price = sequence

        data[filename] = {
            "company": {"company name": company_name},
            "total": {"total price": total_price},
        }

    # Write the processed data to a JSON file with indents
    with open("data.json", "w") as outfile:
        json.dump(data, outfile, indent=2)

def main(argv):
    argumentslist = sys.argv[1:]
    #args should be the path to the images folder and the path to the outputs folder, there should be arguments for the location of the model and the tokenizer along with the output xlsx file
    if len(argumentslist) != 2:
        print("Usage: python image.py <path to images folder> <path to outputs folder> (optional: <path to output xlsx file>) [indev: <path to model> <path to tokenizer>")
        sys.exit(2)
    elif len(argumentslist) == 2:
        image_directory = argumentslist[0]
        output_directory = argumentslist[1]
        start_scan()
        write_to_excel()
        read_and_print_data()
        exit()
    elif len(argumentslist) == 3:
        image_directory = argumentslist[0]
        output_directory = argumentslist[1]
        output_xlsx = argumentslist[2]
        start_scan()
        write_to_excel(output_xlsx)
        read_and_print_data()
        exit()
