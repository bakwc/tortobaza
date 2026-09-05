from pathlib import Path

from fpdf import FPDF

OUTPUT_PATH = Path(__file__).resolve().parent.parent / "sweet_chill_bank_details.pdf"


class BankDetailsPDF(FPDF):
    def header(self):
        self.set_font("Helvetica", "B", 18)
        self.cell(0, 12, "Bank Account Details", align="C", new_x="LMARGIN", new_y="NEXT")
        self.ln(4)

    def field_row(self, label: str, value: str) -> None:
        self.set_font("Helvetica", "B", 11)
        self.cell(45, 10, label)
        self.set_font("Helvetica", "", 11)
        self.cell(0, 10, value, new_x="LMARGIN", new_y="NEXT")


pdf = BankDetailsPDF()
pdf.set_auto_page_break(auto=True, margin=20)
pdf.add_page()
pdf.set_font("Helvetica", "", 11)
pdf.cell(
    0,
    8,
    "Payment details for bank transfer",
    new_x="LMARGIN",
    new_y="NEXT",
)
pdf.ln(6)

pdf.field_row("Beneficiary name:", "SWEET CHILL")
pdf.field_row("IBAN:", "GE94BG0000000612361573")
pdf.field_row("Bank:", "Bank of Georgia")
pdf.field_row("SWIFT:", "BAGAGE22XXX")

pdf.ln(10)
pdf.set_font("Helvetica", "I", 9)
pdf.multi_cell(
    0,
    5,
    "Legal entity: i/m Filip Bakano (NAP305523715)\n"
    "Address: Fridon Khalvashi 2nd Deadlock, 5, Batumi, Georgia\n"
    "Email: info@sweet-chill.ge",
)

pdf.output(str(OUTPUT_PATH))
