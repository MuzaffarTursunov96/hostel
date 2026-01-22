import re
from copy import deepcopy
import numpy as np
import pandas as pd
from lxml import etree
from datetime import datetime


NS_SPREAD = "urn:schemas-microsoft-com:office:spreadsheet"

def add_item(item, val_list, key):
    for i in val_list:
        item[0].append(key)
        item[1].append(i)

def make_role(df_2):
    df_list = [[],[]]
    for key,row in df_2.iterrows():
        if df_2['BP_TYPE'][key] == 'Поставщик':
            add_item(df_list,["000000","FLVN00","FLVN01"],row["P_KEY"])
        if df_2['BP_TYPE'][key] == 'Клиент':
            add_item(df_list,["000000","FLСU00","FLСU01"],row["P_KEY"])
        if df_2['BP_TYPE'][key] == 'Клиент и Поставщик':
            add_item(df_list,["000000","FLVN00","FLVN01","FLСU00","FLСU01"],row["P_KEY"])
    
    return pd.DataFrame({"P_KEY":df_list[0],"BP_ROLE":df_list[1]})


def read_shablon(path):
    df = pd.read_excel(path, sheet_name='BP', header=1, dtype=str)
    
    df.drop([0], axis=0, inplace=True)
   
    df.reset_index(inplace=True, drop=True)
    now = datetime.now()
    prefix = now.strftime("%d%m%y%H%M")  # DDMMYYHHMM
    df["P_KEY"] = prefix + "-" + (df.index + 1).astype(str).str.zfill(5)

    

    df['BU_GROUP'] = df['BU_GROUP'].str.split().str[0]
    df['KTOKK'] = df['BU_GROUP'].str.replace('B', 'K', regex=False)
    df['BU_ADEXT'] = '1'
    df['BUKRS'] = '1000'
    df['KALKS'] = np.where(df['BU_GROUP'] == 'B001', 'G1', 'G2')
    df['LANGU_CORR'] = 'RU'
    df['BP_ROLE'] = '000000'
    df['NAME_1'] = df['NAME'].str[:40]
    df['NAME_2'] = df['NAME'].str[40:80]
    df['NAME_3'] = df['NAME'].str[80:120]
    df['NAME_4'] = df['NAME'].str[120:160]
    df['STREET'] = df['STREET'].str[:60]
    df['ZTERM'] = df['ZTERM'].str.split().str[0]
    df['AKONT'] = df['AKONT'].str.split().str[0]
    df['ZWELS_01'] = df['ZWELS_01'].str.split().str[0]
    df['BANK_NUM'] = df['BANKN'].replace('', np.nan).fillna(df['BANK_IBAN'])  

    # print(df,'dffffff')  
    
    df_for_role = make_role(df[['P_KEY',"BP_TYPE"]])
    df_for_nalog = df[['P_KEY', 'TAXTYPE', 'TAXNUM']].dropna()

    
    return df, df_for_role, df_for_nalog


def q(tag: str) -> str:
    return f"{{{NS_SPREAD}}}{tag}"


def get_cell_data_type(cell_el):
    data = cell_el.find(q("Data"))
    if data is not None:
        return data.get(f"{{{NS_SPREAD}}}Type")
    return None


def _excelize_text(s: str) -> str:
    if s is None:
        return None
    return re.sub(r'\r\n|\r|\n', '  ', s)


def set_cell_value(cell_el, value, preferred_type=None):
    if value is None or (isinstance(value, float) and np.isnan(value)):
        data = cell_el.find(q("Data"))
        if data is not None:
            cell_el.remove(data)
        return

    data = cell_el.find(q("Data"))
    if data is None:
        data = etree.SubElement(cell_el, q("Data"))

    if preferred_type == "DateTime":
        try:
            ts = pd.to_datetime(value)
            data.set(f"{{{NS_SPREAD}}}Type", "DateTime")
            data.text = ts.strftime("%Y-%m-%dT%H:%M:%S")
            return
        except Exception:
            pass

    if preferred_type in {"Number", "Integer"}:
        try:
            num = float(value)
            data.set(f"{{{NS_SPREAD}}}Type", "Number")
            data.text = str(int(num) if float(num).is_integer() else num)
            return
        except Exception:
            pass

    data.set(f"{{{NS_SPREAD}}}Type", "String")
    data.text = _excelize_text("" if value is None else str(value))


def row_to_texts(row_el):
    vals = []
    for cell in row_el.findall(q("Cell")):
        data = cell.find(q("Data"))
        vals.append(data.text if data is not None else "")
    return vals


def get_header_row(table_el, header_row_idx):
    rows = table_el.findall(q("Row"))
    if len(rows) <= header_row_idx:
        raise ValueError("Header (5-qator) topilmadi.")
    return rows[header_row_idx]


def get_tech_headers(table_el, header_row_idx):
    header_row = get_header_row(table_el, header_row_idx)
    headers = []
    for cell in header_row.findall(q("Cell")):
        data = cell.find(q("Data"))
        headers.append(data.text if data is not None else "")
    return headers


def pick_sample_row(table_el, data_start_row_idx):
    rows = table_el.findall(q("Row"))
    if len(rows) > data_start_row_idx:
        return deepcopy(rows[data_start_row_idx])
    return None


def normalize_row_cells_to_headers(row_el, n_cols):
    cells = row_el.findall(q("Cell"))
    if len(cells) < n_cols:
        for _ in range(n_cols - len(cells)):
            row_el.append(etree.Element(q("Cell")))
    elif len(cells) > n_cols:
        for c in cells[n_cols:]:
            row_el.remove(c)


def is_empty_cell(cell_el):
    return cell_el.find(q("Data")) is None


def strip_trailing_empty_cells(row_el):
    cells = row_el.findall(q("Cell"))
    i = len(cells) - 1
    while i >= 0 and is_empty_cell(cells[i]):
        row_el.remove(cells[i])
        i -= 1


def fill_table_with_df(table_el, df: pd.DataFrame, mapping: dict,
                       header_row_idx=4, data_start_row_idx=8, mode="replace"):
    tech_headers = get_tech_headers(table_el, header_row_idx)
    n_cols = len(tech_headers)

    sample_row = pick_sample_row(table_el, data_start_row_idx)
    if sample_row is None:
        sample_row = etree.Element(q("Row"))
        for _ in range(n_cols):
            sample_row.append(etree.Element(q("Cell")))

    if mode == "replace":
        rows = table_el.findall(q("Row"))
        if len(rows) > data_start_row_idx:
            for r in rows[data_start_row_idx:]:
                table_el.remove(r)

    for _, rec in df.iterrows():
        new_row = deepcopy(sample_row)
        normalize_row_cells_to_headers(new_row, n_cols)

        cells = new_row.findall(q("Cell"))
        for col_idx, tech_col in enumerate(tech_headers):
            src = mapping.get(tech_col)
            if src is None:
                val = None
            else:
                if isinstance(src, str) and src in df.columns:
                    val = rec[src]
                else:
                    val = src

            preferred_type = get_cell_data_type(cells[col_idx])
            set_cell_value(cells[col_idx], val, preferred_type=preferred_type)

        strip_trailing_empty_cells(new_row)
        table_el.append(new_row)

    rows_total = len(table_el.findall(q("Row")))
    table_el.set(f"{{{NS_SPREAD}}}ExpandedRowCount", str(rows_total))


def ensure_mso_pi(tree):
    root = tree.getroot()
    node = root.getprevious()
    while node is not None:
        if isinstance(node, etree._ProcessingInstruction) and node.target == 'mso-application':
            return
        node = node.getprevious()
    pi = etree.ProcessingInstruction('mso-application', 'progid="Excel.Sheet"')
    root.addprevious(pi)


def write_with_bom_and_crlf(tree, out_path):
    xml_bytes = etree.tostring(tree, encoding="UTF-8", xml_declaration=True, pretty_print=True)
    xml_bytes = xml_bytes.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")
    bom = b"\xEF\xBB\xBF"
    if not xml_bytes.startswith(bom):
        xml_bytes = bom + xml_bytes
    with open(out_path, "wb") as f:
        f.write(xml_bytes)


def load_xml_tree(input_xml_path: str):
    parser = etree.XMLParser(remove_blank_text=True)
    tree = etree.parse(input_xml_path, parser)
    return tree


def apply_df_to_tree(tree, df: pd.DataFrame, sheet_mappings: dict, mode="replace",
                     header_row_idx=4, data_start_row_idx=8):
    root = tree.getroot()
    for ws in root.findall(q("Worksheet")):
        ws_name = ws.get(f"{{{NS_SPREAD}}}Name")
        if ws_name not in sheet_mappings:
            continue
        table_el = ws.find(q("Table"))
        fill_table_with_df(
            table_el,
            df,
            mapping=sheet_mappings[ws_name],
            header_row_idx=header_row_idx,
            data_start_row_idx=data_start_row_idx,
            mode=mode
        )
    return tree


def save_xml_tree(tree, output_xml_path: str):
    ensure_mso_pi(tree)
    write_with_bom_and_crlf(tree, output_xml_path)


def process_xml(input_xml_path: str, output_xml_path: str, df,
                sheet_mappings, mode="append",
                header_row_idx=4, data_start_row_idx=8):
    tree = load_xml_tree(input_xml_path)
    apply_df_to_tree(
        tree,
        df[0],
        sheet_mappings=sheet_mappings[0],
        mode=mode,
        header_row_idx=header_row_idx,
        data_start_row_idx=data_start_row_idx
    )
    apply_df_to_tree(
        tree,
        df[1],
        sheet_mappings=sheet_mappings[1],
        mode=mode,
        header_row_idx=header_row_idx,
        data_start_row_idx=data_start_row_idx
    )
    apply_df_to_tree(
        tree,
        df[2],
        sheet_mappings=sheet_mappings[2],
        mode=mode,
        header_row_idx=header_row_idx,
        data_start_row_idx=data_start_row_idx
    )
    save_xml_tree(tree, output_xml_path)






import os
from django.conf import settings
from datetime import datetime


def file_generate_bp(path):
    sheet_mappings = [{
        "Общие данные": {'LIFNR': 'P_KEY', 'BU_GROUP': 'BU_GROUP', 'KTOKK': 'KTOKK', 'NAME_FIRST': 'NAME_1', 'NAME_LAST': 'NAME_2', 'NAME3': 'NAME_3', 'NAME4': 'NAME_4', 'SORTL': 'SORTL', 'BU_ADEXT': 'BU_ADEXT', 'STREET': 'STREET', 'HOUSE_NUM1': 'HOUSE_NUM1', 'CITY1': 'CITY1', 'COUNTRY': 'COUNTRY', 'REGION': 'REGION', 'LANGU_CORR': 'LANGU_CORR'},
        "Данные компании": {'LIFNR': 'P_KEY', 'BUKRS': 'BUKRS', 'AKONT': 'AKONT', 'ZTERM1': 'ZTERM', 'ZWELS_01': 'ZWELS_01', 'WAERS': 'WAERS'},
        "Данные закупочной организации": {'LIFNR': 'P_KEY', 'EKORG': '1000', 'WAERS': 'WAERS','WEBRE': 'X', 'KALKS': 'KALKS'},
        "Банковские реквизиты": {'LIFNR': 'P_KEY', 'BANKS': 'BANKS', 'BANKL': 'BANKL', 'BANKN': 'BANKN', 'IBAN': 'BANK_IBAN', 'BKONT': 'BKONT'}},
        {"Роли ДП": {"LIFNR": "P_KEY", 'BP_ROLE': 'BP_ROLE'}},
        {"Налоговые номера":{'LIFNR': 'P_KEY', 'TAXTYPE': 'TAXTYPE', 'TAXNUM': 'TAXNUM'}},
        ]

    df = read_shablon(path)

    # if type(df) == dict:
    #     return '',df

    generated_file_path = "mmg","mmg_bp_generated_" + datetime.now().strftime("%Y%m%d%H%M%S") + ".xml"
    
    input_xml_path = "MDM Source data for Поставщик.xml"
    

    process_xml(
            input_xml_path=input_xml_path, #Bu asosiy shablon, cockpitdan yuklangani
            output_xml_path=generated_file_path, #Bu chiqadigan fayl
            df=df, #Bu exceldan yuklangan DF
            sheet_mappings=sheet_mappings, #bu qaysi betga qaysi ustun yozilishi kere bo'gan dict
            mode="append",  # yoki "replace"
            header_row_idx=4,        # 5-qator (1-based)
            data_start_row_idx=8     # 9-qator (1-based)
        )
    
    return generated_file_path ,[]
