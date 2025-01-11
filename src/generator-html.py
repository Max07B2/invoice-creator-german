#!/usr/bin/python3
import os
import sys
import argparse
import datetime

# set merge_pdf_and_xml = True if the prerequisites are met and the combination of pdf and xml is to be activated
# see near the end of this script
merge_pdf_and_xml = False

# get a cryptographic timestamp for the generated .pdf and .xml files
timestamp_invoice = False

# argument key , description, default value, key in html
argkeys_customer = [
    ["customerCompany", "Name of the company" , "FirmaXYZ", "REC-COMPANY"],
    ["customerName", "Name of the customer", "Max Mustermann" , "REC-NAME"],
    ["customerStreet", "Street of the customer", "Robert-Koch-Str. 12", "REC-STREET"],
    ["customerZIP", "Postal code of the customer", "12345", "REC-ZIP"],
    ["customerCity", "City of the customer", "Musterstadt", "REC-CITY"],
    # ["customerCountry", "Country of the customer", "Germany"]
]

def saveValue(lines, key, value):
    for i in range(len(lines)):
        if lines[i].startswith(key + ";"):
            lines[i] = key + ";" + value + "\n"
            return lines    
    lines.append(key + ";" + value + "\n")
    return lines


def getValue(lines, key, default=''):
    for i in range(len(lines)):
        if lines[i].startswith(key + ";"):
            return lines[i].split(";")[1].replace("\n", "")
    return default


def does_file_exist(file_path):
    return os.path.exists(file_path) and os.path.isfile(file_path)


def get_all_lines_from_file(file_path):
    if not does_file_exist(file_path):
        return []
    with open(file_path, "r") as f:
        return f.readlines()


def is_key_present(csv_lines, key):
    for line in csv_lines:
        if line.split(";")[0] == key:
            if line.split(";")[1].replace("\n", "") != "":
                return True
    return False


# Returns the second csv field.
def get_value(csv_lines, key, default = ""):
    for line in csv_lines:
        if line.split(";")[0] == key:
            return line.split(";")[1]
    return default


def convert_to_euro_string(template_lines, value):
    value = str(round(float(value), 2))
    if value.find(".") == -1:
        value += ",00"
    value = value.replace(".", ",")
    # If value ends only with one digit, add a 0
    if value[len(value) - 2] == ",":
        value += "0"
    currency = get_value(template_lines, "CURRENCY", "€")
    return value + " " + currency
    

def main():
    # get home directory
    home = os.path.expanduser("~")
    # create cache directory
    cache_dir = home + "/.cache/rechnungs-assistent/"
    config_dir = home + "/.config/rechnungs-assistent/"

    current_dir = os.path.dirname(os.path.realpath(__file__))

    # If cache directory does not exist, create it
    if not os.path.exists(cache_dir):
        os.makedirs(cache_dir)

    # empty cache directory
    os.system(f"rm -f {cache_dir}/*")

    # If config directory does not exist, create it
    if not os.path.exists(config_dir):
        os.makedirs(config_dir)

    # If template.csv does not exist, copy the example to the config folder
    if not does_file_exist(f"{config_dir}/template.csv"):
        os.system("cp {{current_dir}}/html/template.csv.example " + config_dir + "/template.csv")

    # Create the parser
    parser = argparse.ArgumentParser(description='German invoice generator.')

    # Add arguments for customer data
    for i in range(len(argkeys_customer)):
        # make them mandatory
        parser.add_argument('--' + argkeys_customer[i][0], help=argkeys_customer[i][1])


    # Add article arguments with price, amount and description
    parser.add_argument('--article', nargs='+', help='One or more articles. Format: --article "<description>;<pricePerUnit>;<amount>;<summary>" "<description>;<pricePerUnit>;<amount>;<summary>"')
    # Discount
    parser.add_argument('--discount', help='Discount in euro. Format: --discount "Discount;25"')

    # Path to the template file
    parser.add_argument('--template', help='Path to the template file. Default: template.csv', default=f'{config_dir}/template.csv')

    # Get number of payment days
    parser.add_argument('--paymentDays', help='Number of days until payment is due. Default: 14', default='14')

    # Overrice the invoice number
    parser.add_argument('--invoiceNumber', help='Invoice number if you want to override. Default: YYYY-MM-<number>', default='')

    # "Leistungsdatum"
    parser.add_argument('--serviceDate', help='Service date. Default: "today"', default='today')

    # Path to logo
    parser.add_argument('--logo', help='Path to the logo. Default: logo.png', default='')

    # dry run
    parser.add_argument('--dryRun', help='Dry run. Do not save the pdf to the invoice Dir.', action='store_true')

    # Path to the invoice directory structure (rechnungen/currentyear/currentmonth)
    parser.add_argument('--invoiceDir', help='Path to the invoice directory structure. Default: invoices', default=f'{home}/Dokumente/Rechnungen/')

    # Parse the command-line arguments
    args = parser.parse_args()

    print("Generating invoice...")

    # Get all lines from the invoice.html template
    lines = get_all_lines_from_file(f"{current_dir}/html/invoice.html")
    if len(lines) == 0:
        print(f'Error: Could not open template file: "{current_dir}/html/invoice.html"')
        sys.exit(1)

    # Get key and value from the template.csv
    template_lines = get_all_lines_from_file(args.template)
    if len(template_lines) == 0:
        print(f'Error: Could not open template file: "{args.template}"')
        sys.exit(1)

    # Get date
    date = datetime.datetime.now().strftime("%d.%m.%Y")
    payment_date = (datetime.datetime.now() + datetime.timedelta(days=int(args.paymentDays))).strftime("%d.%m.%Y")

    # INVOICE NUMBER
    # Ensure that this directory exists: invoices/currentyear/currentmonth
    current_year = datetime.datetime.now().strftime("%Y")
    current_month = datetime.datetime.now().strftime("%m")
    # if the invoice directory does not exist, create it
    invoice_dir = args.invoiceDir + "/" + current_year + "/" + current_month
    if not os.path.exists(invoice_dir):
        os.makedirs(invoice_dir)
    # Generate invoice number from amount of .pdf files in the invoice folder Format: YYYY-MM-<number>
    # Get all files in the invoice directory
    files = os.listdir(invoice_dir)
    # Check every file for .pdf
    number = 1
    for file in files:
        if file.endswith("_o.pdf"):
            number += 1
    invoice_number = datetime.datetime.now().strftime("%Y-%m-") + str(number)
    if args.invoiceNumber != "":
        invoice_number = args.invoiceNumber



    # Get Articles
    articles = []
    articles_string_list = args.article
    if articles_string_list != None:
        for article_string in articles_string_list:
            # Parse the article
            segments = article_string.split(";")
            if len(segments) != 4:
                print(f'Error: Wrong format for article: "{article_string}". Use: --article "<description>;<pricePerUnit>;<amount>;<summary>" "<description>;<pricePerUnit>;<amount>;<summary>"')
                sys.exit(1)
            articles.append(segments)

     
    # Get Discount
    discounts = []
    discount_string = args.discount
    if discount_string != None:
        segments = discount_string.split(";")
        if len(segments) != 2:
            print(f'Error: Wrong format for discount: "{discount_string}". Use: --discount "Discount;10"')
            sys.exit(1)
        discounts.append(segments)


    # Generate html code for articles
    # Example: 
    #   <tr>
    #     <td class="invoice-item-name">Product 1</td>
    #     <td>$10.00</td>
    #     <td>1</td>
    #     <td>$10.00</td>
    #   </tr>
    table_html = ""
    for article in articles:
        description = ""
        if article[3] != "":
            description = f'<br>{article[3]}'
        table_html += f'<tr style="page-break-inside:avoid;"><td class="invoice-item-name"><strong>{article[0]}</strong>{description}</td><td>{convert_to_euro_string(template_lines, article[1])}</td><td>{article[2]}</td><td>{convert_to_euro_string(template_lines, float(article[1]) * float(article[2]))}</td></tr>\n'

    for discount in discounts:
        table_html += f'<tr style="page-break-inside:avoid;"><td class="invoice-item-name">{discount[0]}</td><td> - </td><td> - </td><td>- {convert_to_euro_string(template_lines, discount[1])}</td></tr>\n'
    
    # Calculate sum
    sum_netto = 0
    for article in articles:
        # Article price per unit * amount
        sum_netto += float(article[1]) * float(article[2])
    for discount in discounts:
        # Discount price
        sum_netto -= float(discount[1])
    
    vat = float(get_value(template_lines, "DEFAULT-VAT"))
    vat_sum = sum_netto * (vat / 100)
    sum_brutto = sum_netto + vat_sum


    # Generate html for sender info
    sen_info_description = ""
    sen_info_data = ""
    if is_key_present(template_lines, "SEN-COMPANY"):
        sen_company = get_value(template_lines, "SEN-COMPANY").strip()
        sen_info_description +=  """  <tr> \n"""
        sen_info_description +=  """        <td style="text-align: right;"></td> \n"""
        sen_info_description += f"""        <td style="text-align: left;"><strong>{sen_company}</strong></td> \n"""
        sen_info_description +=  """      </tr> \n"""
    if is_key_present(template_lines, "SEN-NAME") and is_key_present(template_lines, "SEN-STREET") and is_key_present(template_lines, "SEN-CITY"):
        sen_name = get_value(template_lines, "SEN-NAME").strip()
        sen_street = get_value(template_lines, "SEN-STREET").strip()
        sen_zip = get_value(template_lines, "SEN-ZIP").strip()
        sen_city = get_value(template_lines, "SEN-CITY").strip()
        sen_info_description +=  """      <tr> \n"""
        sen_info_description +=  """        <td style="text-align: right;">Anschrift</td> \n"""
        sen_info_description += f"""        <td style="text-align: left;">{sen_name}<br>{sen_street}<br>{sen_zip} {sen_city}</td> \n"""
        sen_info_description +=  """      </tr> \n"""
    if is_key_present(template_lines, "SEN-EMAIL"):
        sen_email = get_value(template_lines, "SEN-EMAIL").strip()
        sen_info_description +=  """      <tr> \n"""
        sen_info_description +=  """        <td style="text-align: right;">E-Mail</td> \n"""
        sen_info_description += f"""        <td style="text-align: left;"><a style=\"color: grey; text-decoration: none;\" href=\"mailto:{sen_email}\">{sen_email}</a></td> \n"""
        sen_info_description +=  """      </tr> \n"""
    if is_key_present(template_lines, "SEN-PHONE"):
        sen_phone = get_value(template_lines, "SEN-PHONE").strip()
        sen_info_description +=  """      <tr> \n"""
        sen_info_description +=  """        <td style="text-align: right;">Telefon</td> \n"""
        sen_info_description += f"""        <td style="text-align: left;"><a style=\"color: grey; text-decoration: none;\" href=\"tel:{sen_phone}\">{sen_phone}</a></td> \n"""
        sen_info_description +=  """      </tr> \n"""
    if is_key_present(template_lines, "SEN-WEBSITE"):
        sen_website = get_value(template_lines, "SEN-WEBSITE").strip()
        sen_info_description +=  """      <tr> \n"""
        sen_info_description +=  """        <td style="text-align: right;">Website</td> \n"""
        sen_info_description += f"""        <td style="text-align: left;"><a style=\"color: grey; text-decoration: none;\" href=\"https://{sen_website}\">{sen_website}</a></td> \n"""
        sen_info_description +=  """      </tr> \n"""
    sen_info_description +=  """      <tr> \n"""
    sen_info_description +=  """        <td style="text-align: right;">&nbsp;</td> \n"""
    sen_info_description += f"""        <td style="text-align: left;">&nbsp;</td> \n"""
    sen_info_description +=  """      </tr> \n"""
    if is_key_present(template_lines, "SEN-TAX-ID"):
        sen_tax_id = get_value(template_lines, "SEN-TAX-ID").strip()
        sen_info_description +=  """      <tr> \n"""
        sen_info_description +=  """        <td style="text-align: right;">Ust-IdNr.</td> \n"""
        sen_info_description += f"""        <td style="text-align: left;">{sen_tax_id}</td> \n"""
        sen_info_description +=  """      </tr> \n"""
    sen_info_description +=  """      <tr> \n"""
    sen_info_description +=  """        <td style="text-align: right;">&nbsp;</td> \n"""
    sen_info_description += f"""        <td style="text-align: left;">&nbsp;</td> \n"""
    sen_info_description +=  """      </tr> \n"""

    if is_key_present(template_lines, "MONEY-INSTITUTE"):
        sen_money_institute = get_value(template_lines, "MONEY-INSTITUTE").strip()
        sen_info_description +=  """      <tr> \n"""
        sen_info_description +=  """        <td style="text-align: right;">Institut</td> \n"""
        sen_info_description += f"""        <td style="text-align: left;">{sen_money_institute}</td> \n"""
        sen_info_description +=  """      </tr> \n"""
    if is_key_present(template_lines, "IBAN"):
        sen_iban = get_value(template_lines, "IBAN").strip()
        sen_info_description +=  """      <tr> \n"""
        sen_info_description +=  """        <td style="text-align: right;">IBAN</td> \n"""
        sen_info_description += f"""        <td style="text-align: left;">{sen_iban}</td> \n"""
        sen_info_description +=  """      </tr> \n"""
    if is_key_present(template_lines, "BIC"):
        sen_bic = get_value(template_lines, "BIC").strip()
        sen_info_description +=  """      <tr> \n"""
        sen_info_description +=  """        <td style="text-align: right;">BIC</td> \n"""
        sen_info_description += f"""        <td style="text-align: left;">{sen_bic}</td> \n"""
        sen_info_description +=  """      </tr> \n"""
    sen_info_description +=  """      <tr> \n"""
    sen_info_description +=  """        <td style="text-align: right;">&nbsp;</td> \n"""
    sen_info_description += f"""        <td style="text-align: left;">&nbsp;</td> \n"""
    sen_info_description +=  """      </tr> \n"""

    # Add invoiceDate to the table in sen_info section
    sen_info_description +=  """      <tr> \n"""
    sen_info_description +=  """        <td style="text-align: right;">Rechnungsdatum</td> \n"""
    sen_info_description += f"""        <td style="text-align: left;">{date}</td> \n"""
    sen_info_description +=  """      </tr> \n"""

    # Add invoiceNumber to the table in sen_info section
    sen_info_description +=  """      <tr> \n"""
    sen_info_description +=  """        <td style="text-align: right;">Rechnungsnummer</td> \n"""
    sen_info_description += f"""        <td style="text-align: left;">{invoice_number}</td> \n"""
    sen_info_description +=  """      </tr> \n"""

    # Add serviceDate (Leistungsdatum) to the table in sen_info section
    if args.serviceDate == "today":
        args.serviceDate = date
    sen_info_description +=  """      <tr> \n"""
    sen_info_description +=  """        <td style="text-align: right;">Leistungsdatum</td> \n"""
    sen_info_description += f"""        <td style="text-align: left;">{args.serviceDate}</td> \n"""
    sen_info_description +=  """      </tr> \n"""

    # Add two rows as space after the table
    sen_info_description +=  """      <tr> \n"""
    sen_info_description +=  """        <td style="text-align: right;">&nbsp;</td> \n"""
    sen_info_description += f"""        <td style="text-align: left;">&nbsp;</td> \n"""
    sen_info_description +=  """      </tr> \n"""
    sen_info_description +=  """      <tr> \n"""
    sen_info_description +=  """        <td style="text-align: right;">&nbsp;</td> \n"""
    sen_info_description += f"""        <td style="text-align: left;">&nbsp;</td> \n"""
    sen_info_description +=  """      </tr> \n"""

    # Replace all keys with the values (GENERATE THE HTML FILE)
    for i in range(len(lines)):
        # Template data
        for j in range(len(template_lines)):
            lines[i] = lines[i].replace("#!" + template_lines[j].split(";")[0], template_lines[j].split(";")[1].replace("\n", ""))


        # Customer data
        for j in range(len(argkeys_customer)):
            if type(args.__dict__[argkeys_customer[j][0]]) == str and args.__dict__[argkeys_customer[j][0]] != "":
                lines[i] = lines[i].replace("#!" + argkeys_customer[j][3], args.__dict__[argkeys_customer[j][0]])

        # Date
        lines[i] = lines[i].replace("#!DATE", date)
        lines[i] = lines[i].replace("#!PAY-DATE", payment_date)

        # Invoice number
        lines[i] = lines[i].replace("#!INVOICE-NUM", invoice_number)

        # Sum with VAT
        lines[i] = lines[i].replace("#!SUM-WITHOUT-VAT", convert_to_euro_string(template_lines, sum_netto))
        lines[i] = lines[i].replace("#!VAT-PERCENT", str(vat) + " %")
        lines[i] = lines[i].replace("#!VAT-ADDITION", convert_to_euro_string(template_lines, vat_sum))
        lines[i] = lines[i].replace("#!SUM-WITH-VAT", convert_to_euro_string(template_lines, sum_brutto))

        # Table
        lines[i] = lines[i].replace("#!ITEMS", table_html)

        # Sender info
        lines[i] = lines[i].replace("#!SEN-INFO-DESCRIPTION", sen_info_description)
        lines[i] = lines[i].replace("#!SEN-INFO-DATA", sen_info_data)

    # Remove all lines that have a #!
    for i in range(len(lines)):
        if lines[i].find("#!") != -1:
            lines[i] = ""

    # Save .html file to cache
    f = open(f"{cache_dir}/invoice.html", "w")
    f.writelines(lines)
    f.close()

    logo_path = get_value(template_lines, "ICON-PATH")
    if args.logo != "":
        logo_path = args.logo
    logo_path = logo_path.replace("//", "/").strip()
    print("Logo path: " + logo_path)
    print("Template Dir: " + os.path.dirname(args.template))
    # Copy logo to cache dir.
    if logo_path != "":
        if not os.path.exists(logo_path):
            # Try with local path directly next to the template.csv
            # Get the path of the template.csv
            template_dir = os.path.dirname(args.template)
            logo_path = template_dir + "/" + logo_path
            logo_path = logo_path.replace("//", "/").strip()
            if not os.path.exists(logo_path):
                print(f'Error: Could not open logo file: "{logo_path}"')
                # Copy the default logo
                os.system(f"cp {current_dir}/html/logo.png {cache_dir}/logo.png")
            else:
                os.system(f"cp \"{logo_path}\" {cache_dir}/logo.png")
        else:
            os.system(f"cp \"{logo_path}\" {cache_dir}/logo.png")
    else:
        # Copy the default logo
        os.system(f"cp {current_dir}/html/logo.png {cache_dir}/logo.png")


    print_path = f"{invoice_dir}/Rechnung-{invoice_number}.pdf"
    if args.dryRun:
        print("Dry run. Not saving the pdf to the invoice Dir.")
        print_path = f"{cache_dir}/Rechnung.pdf"

    # Check if chromium folder is present next to the script
    chromium_exec = ""
    if os.path.exists(f"{current_dir}/chromium"):
        chromium_exec = f"{current_dir}/chromium/chrome"
    else:
        chromium_exec = "chromium"


    os.system(f"{chromium_exec} --no-sandbox --headless --disable-gpu --print-to-pdf={cache_dir}/invoice.pdf --no-margins --no-pdf-header-footer  file://{cache_dir}/invoice.html ")

    currency = get_value(template_lines, "CURRENCY", "€")
    if currency == "€":
        currency = "EUR"
    elif currency == "$":
        currency = "USD"

    invoice_message = get_value(template_lines, "MESSAGE", "")
    invoice_message = invoice_message.replace("#!INVOICE-NUM", invoice_number)
    invoice_message = invoice_message.replace("#!PAY-DATE", payment_date)

    lines = []

    lines.append("<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n")
    lines.append("<rsm:CrossIndustryInvoice xmlns:rsm=\"urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100\" xmlns:qdt=\"urn:un:unece:uncefact:data:standard:QualifiedDataType:100\" xmlns:ram=\"urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100\" xmlns:xs=\"http://www.w3.org/2001/XMLSchema\" xmlns:udt=\"urn:un:unece:uncefact:data:standard:UnqualifiedDataType:100\">\n")
    lines.append("  <rsm:ExchangedDocumentContext>\n")
    lines.append("    <ram:GuidelineSpecifiedDocumentContextParameter>\n")
    lines.append("      <ram:ID>urn:cen.eu:en16931:2017</ram:ID>\n")
    lines.append("    </ram:GuidelineSpecifiedDocumentContextParameter>\n")
    lines.append("  </rsm:ExchangedDocumentContext>\n")
    lines.append("  <rsm:ExchangedDocument>\n")
    lines.append("    <ram:IncludedNote>\n")
    lines.append("      <ram:Content>" + invoice_message + "</ram:Content>\n")
    lines.append("    </ram:IncludedNote>\n")
    lines.append("    <ram:ID>" + invoice_number + "</ram:ID>\n")
    lines.append("    <ram:TypeCode>380</ram:TypeCode>\n")
    lines.append("    <ram:IssueDateTime>\n")
    lines.append("      <udt:DateTimeString format=\"102\">" + datetime.datetime.now().strftime("%Y%m%d") + "</udt:DateTimeString>\n")
    lines.append("    </ram:IssueDateTime>\n")
    lines.append("  </rsm:ExchangedDocument>\n")
    lines.append("  <rsm:SupplyChainTradeTransaction>\n")
    lines.append("    <ram:ApplicableHeaderTradeAgreement>\n")
    lines.append("      <ram:SellerTradeParty>\n")
    lines.append("        <ram:ID></ram:ID>\n")
    lines.append("        <ram:GlobalID schemeID=\"0088\"></ram:GlobalID>\n")
    lines.append("        <ram:Name>" + sen_company + "</ram:Name>\n")
    lines.append("        <ram:PostalTradeAddress>\n")
    lines.append("          <ram:PostcodeCode>" + sen_zip + "</ram:PostcodeCode>\n")
    lines.append("          <ram:LineOne>" + sen_street + "</ram:LineOne>\n")
    lines.append("          <ram:CityName>" + sen_city + "</ram:CityName>\n")
    lines.append("          <ram:CountryID></ram:CountryID>\n")
    lines.append("        </ram:PostalTradeAddress>\n")
    lines.append("        <ram:SpecifiedTaxRegistration>\n")
    lines.append("          <ram:ID schemeID=\"FC\">" + sen_tax_id + "</ram:ID>\n")
    lines.append("        </ram:SpecifiedTaxRegistration>\n")
    lines.append("        <ram:SpecifiedTaxRegistration>\n")
    lines.append("          <ram:ID schemeID=\"VA\">" + sen_tax_id + "</ram:ID>\n")
    lines.append("        </ram:SpecifiedTaxRegistration>\n")
    lines.append("      </ram:SellerTradeParty>\n")

    customer_name = (args.customerCompany + " " + args.customerName).strip()
    lines.append("  <ram:BuyerTradeParty>\n")
    lines.append("    <ram:ID></ram:ID>\n")
    lines.append("    <ram:Name>" + customer_name + "</ram:Name>\n")
    lines.append("    <ram:PostalTradeAddress>\n")
    lines.append("      <ram:PostcodeCode>" + args.customerZIP + "</ram:PostcodeCode>\n")
    lines.append("      <ram:LineOne>" + args.customerStreet + "</ram:LineOne>\n")
    lines.append("      <ram:CityName>" + args.customerCity + "</ram:CityName>\n")
    lines.append("      <ram:CountryID></ram:CountryID>\n")
    lines.append("    </ram:PostalTradeAddress>\n")
    lines.append("  </ram:BuyerTradeParty>\n")

    lines.append("    </ram:ApplicableHeaderTradeAgreement>\n")
    lines.append("    <ram:ApplicableHeaderTradeSettlement>\n")
    lines.append("      <ram:InvoiceCurrencyCode>" + currency + "</ram:InvoiceCurrencyCode>\n")
    lines.append("      <ram:ApplicableTradeTax>\n")
    lines.append("        <ram:CalculatedAmount>" + str(vat_sum) + "</ram:CalculatedAmount>\n")
    lines.append("        <ram:TypeCode>VAT</ram:TypeCode>\n")
    lines.append("        <ram:BasisAmount>" + str(sum_netto) + "</ram:BasisAmount>\n")
    lines.append("        <ram:CategoryCode>S</ram:CategoryCode>\n")
    lines.append("        <ram:RateApplicablePercent>" + str(vat) + "</ram:RateApplicablePercent>\n")
    lines.append("      </ram:ApplicableTradeTax>\n")
    lines.append("      <ram:SpecifiedTradeSettlementHeaderMonetarySummation>\n")
    lines.append("        <ram:LineTotalAmount>" + str(sum_brutto) + "</ram:LineTotalAmount>\n")
    lines.append("        <ram:ChargeTotalAmount>0.00</ram:ChargeTotalAmount>\n")
    lines.append("        <ram:AllowanceTotalAmount>0.00</ram:AllowanceTotalAmount>\n")
    lines.append("        <ram:TaxBasisTotalAmount>" + str(sum_netto) + "</ram:TaxBasisTotalAmount>\n")
    lines.append("        <ram:TaxTotalAmount currencyID=\"" + currency + "\">" + str(vat_sum) + "</ram:TaxTotalAmount>\n")
    lines.append("        <ram:GrandTotalAmount>" + str(sum_brutto) + "</ram:GrandTotalAmount>\n")
    lines.append("        <ram:TotalPrepaidAmount>0.00</ram:TotalPrepaidAmount>\n")
    lines.append("        <ram:DuePayableAmount>" + str(sum_brutto) + "</ram:DuePayableAmount>\n")
    lines.append("      </ram:SpecifiedTradeSettlementHeaderMonetarySummation>\n")
    lines.append("      <ram:SpecifiedTradeSettlementFinancialCard>\n")
    lines.append("        <ram:ID schemeID=\"IBAN\">" + sen_iban + "</ram:ID>\n")
    lines.append("        <ram:CardholderName>" + sen_company + "</ram:CardholderName>\n")
    lines.append("      </ram:SpecifiedTradeSettlementFinancialCard>\n")
    lines.append("      <ram:SpecifiedTradeSettlementPaymentMeans>\n")
    lines.append("        <ram:TypeCode>58</ram:TypeCode>\n")
    lines.append("        <ram:Information>Zahlung per SEPA Überweisung.</ram:Information>\n")
    lines.append("        <ram:PayeePartyCreditorFinancialAccount>\n")
    lines.append("          <ram:IBANID>" + sen_iban + "</ram:IBANID>\n")
    lines.append("          <ram:AccountName>" + sen_company + "</ram:AccountName>\n")
    lines.append("        </ram:PayeePartyCreditorFinancialAccount>\n")
    lines.append("        <ram:PayeeSpecifiedCreditorFinancialInstitution>\n")
    lines.append("          <ram:BICID>" + sen_bic + "</ram:BICID>\n")
    lines.append("        </ram:PayeeSpecifiedCreditorFinancialInstitution>\n")
    lines.append("      </ram:SpecifiedTradeSettlementPaymentMeans>\n")
    lines.append("      <ram:SpecifiedTradePaymentTerms>\n")
    lines.append("        <ram:DueDateDateTime>\n")
    lines.append("          <udt:DateTimeString format=\"102\">" + (datetime.datetime.now() + datetime.timedelta(days=int(args.paymentDays))).strftime("%Y%m%d") + "</udt:DateTimeString>\n")
    lines.append("        </ram:DueDateDateTime>\n")
    lines.append("      </ram:SpecifiedTradePaymentTerms>\n")
    lines.append("    </ram:ApplicableHeaderTradeSettlement>\n")
    print(articles)
    i=0
    for article in articles:
        lines.append("    <ram:IncludedSupplyChainTradeLineItem>\n")
        lines.append("      <ram:AssociatedDocumentLineDocument>\n")
        lines.append("        <ram:LineID>" + str(i + 1) + "</ram:LineID>\n")
        lines.append("      </ram:AssociatedDocumentLineDocument>\n")
        lines.append("      <ram:SpecifiedTradeProduct>\n")
        lines.append("        <ram:Name>" + str(article[0]) + "</ram:Name>\n")
        lines.append("      </ram:SpecifiedTradeProduct>\n")
        lines.append("      <ram:SpecifiedLineTradeAgreement>\n")
        lines.append("        <ram:GrossPriceProductTradePrice>\n")
        lines.append("          <ram:ChargeAmount>" + str(article[1]) + "</ram:ChargeAmount>\n")
        lines.append("        </ram:GrossPriceProductTradePrice>\n")
        lines.append("        <ram:NetPriceProductTradePrice>\n")
        lines.append("          <ram:ChargeAmount>" + str(article[1]) + "</ram:ChargeAmount>\n")
        lines.append("        </ram:NetPriceProductTradePrice>\n")
        lines.append("      </ram:SpecifiedLineTradeAgreement>\n")
        lines.append("      <ram:SpecifiedLineTradeDelivery>\n")
        lines.append("        <ram:BilledQuantity unitCode=\"H87\">" + str(article[2]) + "</ram:BilledQuantity>\n")
        lines.append("      </ram:SpecifiedLineTradeDelivery>\n")
        lines.append("      <ram:SpecifiedLineTradeSettlement>\n")
        lines.append("        <ram:ApplicableTradeTax>\n")
        lines.append("          <ram:TypeCode>VAT</ram:TypeCode>\n")
        lines.append("          <ram:CategoryCode>S</ram:CategoryCode>\n")
        lines.append("          <ram:RateApplicablePercent>" + str(vat) + "</ram:RateApplicablePercent>\n")
        lines.append("        </ram:ApplicableTradeTax>\n")
        lines.append("        <ram:SpecifiedTradeSettlementLineMonetarySummation>\n")
        lines.append("          <ram:LineTotalAmount>" + str(float(article[1]) * float(article[2])) + "</ram:LineTotalAmount>\n")
        lines.append("        </ram:SpecifiedTradeSettlementLineMonetarySummation>\n")
        lines.append("      </ram:SpecifiedLineTradeSettlement>\n")
        lines.append("    </ram:IncludedSupplyChainTradeLineItem>\n")
        i=i+1
    print(discounts)
    i=0
    for discount in discounts:
        lines.append("    <ram:IncludedSupplyChainTradeLineItem>\n")
        lines.append("      <ram:AssociatedDocumentLineDocument>\n")
        lines.append("        <ram:LineID>" + str(i + 1) + "</ram:LineID>\n")
        lines.append("      </ram:AssociatedDocumentLineDocument>\n")
        lines.append("      <ram:SpecifiedTradeProduct>\n")
        lines.append("        <ram:Name>" + str(discount[0]) + "</ram:Name>\n")
        lines.append("      </ram:SpecifiedTradeProduct>\n")
        lines.append("      <ram:SpecifiedLineTradeAgreement>\n")
        lines.append("        <ram:GrossPriceProductTradePrice>\n")
        lines.append("          <ram:ChargeAmount>-" + str(discount[1]) + "</ram:ChargeAmount>\n")
        lines.append("        </ram:GrossPriceProductTradePrice>\n")
        lines.append("        <ram:NetPriceProductTradePrice>\n")
        lines.append("          <ram:ChargeAmount>-" + str(discount[1]) + "</ram:ChargeAmount>\n")
        lines.append("        </ram:NetPriceProductTradePrice>\n")
        lines.append("      </ram:SpecifiedLineTradeAgreement>\n")
        lines.append("      <ram:SpecifiedLineTradeSettlement>\n")
        lines.append("        <ram:ApplicableTradeTax>\n")
        lines.append("          <ram:TypeCode>VAT</ram:TypeCode>\n")
        lines.append("          <ram:CategoryCode>S</ram:CategoryCode>\n")
        lines.append("          <ram:RateApplicablePercent>" + str(vat) + "</ram:RateApplicablePercent>\n")
        lines.append("        </ram:ApplicableTradeTax>\n")
        lines.append("        <ram:SpecifiedTradeSettlementLineMonetarySummation>\n")
        lines.append("          <ram:LineTotalAmount>-" + str(discount[1]) + "</ram:LineTotalAmount>\n")
        lines.append("        </ram:SpecifiedTradeSettlementLineMonetarySummation>\n")
        lines.append("      </ram:SpecifiedLineTradeSettlement>\n")
        lines.append("    </ram:IncludedSupplyChainTradeLineItem>\n")
        i=i+1
    lines.append("  </rsm:SupplyChainTradeTransaction>\n")
    lines.append("</rsm:CrossIndustryInvoice>\n")
    
    f = open(f"{cache_dir}/invoice.xml", "w")
    f.writelines(lines)
    f.close()

    # timestamp the original files
    if timestamp_invoice:
        os.system(f"openssl ts -query -data {cache_dir}/invoice.pdf -no_nonce -sha512 -cert -out {cache_dir}/invoice.pdf.tsq")
        os.system(f"""curl -H "Content-Type: application/timestamp-query" --data-binary '@{cache_dir}/invoice.pdf.tsq' http://timestamp.digicert.com > {cache_dir}/invoice.pdf.tsr""")
        os.system(f"openssl ts -verify -data {cache_dir}/invoice.pdf -in {cache_dir}/invoice.pdf.tsr -CAfile ../timestamp/cacerts.pem")

        os.system(f"openssl ts -query -data {cache_dir}/invoice.xml -no_nonce -sha512 -cert -out {cache_dir}/invoice.xml.tsq")
        os.system(f"""curl -H "Content-Type: application/timestamp-query" --data-binary '@{cache_dir}/invoice.xml.tsq' http://timestamp.digicert.com > {cache_dir}/invoice.xml.tsr""")
        os.system(f"openssl ts -verify -data {cache_dir}/invoice.xml -in {cache_dir}/invoice.xml.tsr -CAfile ../timestamp/cacerts.pem")
    
    # Create the combined pdf+xml file
    
    if merge_pdf_and_xml:
        # preconditions for this implementation
        # - pdftops from the Poppler project (http://poppler.freedesktop.org)
        # - gs (Ghostscript)
        # - ../mustang-cli/Mustang-CLI-2.15.2.jar from the Mustang project (https://www.mustangproject.org)

        # step 1: convert pdf to ps with poppler
        os.system(f"pdftops {cache_dir}/invoice.pdf {cache_dir}/invoice.ps")
        
        # step 2: convert ps to pdf/a-1 with gs
        os.system(f"gs -dPDFA -dBATCH -dNOPAUSE -sColorConversionStrategy=UseDeviceIndependentColor -sDEVICE=pdfwrite -dPDFACompatibilityPolicy=1 -sOutputFile={cache_dir}/invoice_a.pdf {cache_dir}/invoice.ps")
        
        # step 3: combine pdf/a-1 an xml to one pdf/a-1 file with the mustang library
        os.system(f"java -Xmx1G -Dfile.encoding=UTF-8 -jar ../mustang-cli/Mustang-CLI-2.15.2.jar --action combine -source {cache_dir}/invoice_a.pdf -source-xml {cache_dir}/invoice.xml -out {cache_dir}/invoice_c.pdf -attachments '' -format zf -version 2 -profile x")

        # timestamp file
        if timestamp_invoice:
            os.system(f"openssl ts -query -data {cache_dir}/invoice_c.pdf -no_nonce -sha512 -cert -out {cache_dir}/invoice_c.pdf.tsq")
            os.system(f"""curl -H "Content-Type: application/timestamp-query" --data-binary '@{cache_dir}/invoice_c.pdf.tsq' http://timestamp.digicert.com > {cache_dir}/invoice_c.pdf.tsr""")
            os.system(f"openssl ts -verify -data {cache_dir}/invoice_c.pdf -in {cache_dir}/invoice_c.pdf.tsr -CAfile ../timestamp/cacerts.pem")

    # Copy the generated files to the invoice directory

    # - original pdf - gets renamed to invoice_o.pdf for the invoice number generation algorithm
    print_path = print_path.replace(".pdf", "_o.pdf")
    os.system(f"cp {cache_dir}/invoice.pdf {print_path}")

    # - original xml - gets also renamed to invoice_o.xml
    print_path_xml = print_path.replace("_o.pdf", "_o.xml")
    os.system(f"cp {cache_dir}/invoice.xml {print_path_xml}")

    # - timestamp file
    if timestamp_invoice:
        os.system(f"cp {cache_dir}/invoice.pdf.tsq {print_path}.tsq")
        os.system(f"cp {cache_dir}/invoice.pdf.tsr {print_path}.tsr")

        os.system(f"cp {cache_dir}/invoice.xml.tsq {print_path_xml}.tsq")
        os.system(f"cp {cache_dir}/invoice.xml.tsr {print_path_xml}.tsr")

    # - combined pdf 
    if merge_pdf_and_xml:
        print_path = print_path.replace("_o.pdf", "_c.pdf")
        os.system(f"cp {cache_dir}/invoice_c.pdf {print_path}")

        # - timestamp file
        if timestamp_invoice:
            os.system(f"cp {cache_dir}/invoice_c.pdf.tsq {print_path}.tsq")
            os.system(f"cp {cache_dir}/invoice_c.pdf.tsr {print_path}.tsr")

    print("InvoicePath: " + print_path)
    pass

if __name__ == "__main__":
    main()
