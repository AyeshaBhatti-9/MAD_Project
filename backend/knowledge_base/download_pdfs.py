import requests
import os
import time

PDF_URLS = [





    "https://drs.molaw.gov.pk/pdf/The%20Islamabad%20Capital%20Territory%20Domestic%20Workers%20Act,%202022.%20.pdf",
    "https://drs.molaw.gov.pk/pdf/The%20Maternity%20and%20Paternity%20Leave%20Act,%202023.pdf",
    "https://drs.molaw.gov.pk/pdf/National%20Asembly%20Secretariat%20Employees%20Act%202018.pdf",
    "https://drs.molaw.gov.pk/pdf/The%20Industrial%20Relation%20Ordinance,%202011%20(1).pdf",
    "https://drs.molaw.gov.pk/pdf/The%20Sacked%20Employees%20(Reinstatement)%20Ordinance,%202009.%202.pdf",
    "https://drs.molaw.gov.pk/pdf/The%20Islamabad%20Capital%20Territory%20Shops,%20Business%20and%20Industrial%20Establishments%20(Security)%20Ordinance,%202000..pdf",
    "https://drs.molaw.gov.pk/pdf/The%20Medical%20Officers%20(Regularization%20of%20Appointments)%20Act,%201992%20%20XVI.pdf",
    "https://drs.molaw.gov.pk/pdf/The%20Bonded%20Labour%20System%20(Abolition)%20Act,%201992%20%20III.pdf",
    "https://drs.molaw.gov.pk/pdf/XVIII.%20The%20Emigration%20Ordinance,%201979%20(1).pdf",
    "https://drs.molaw.gov.pk/pdf/LXXVII.%20The%20Fee-Charging%20Employment%20Agencies%20(Regulation)%20Act,%201976.pdf",
    "https://drs.molaw.gov.pk/pdf/XIV.%20The%20Employees'%20Old-Age%20Benefits%20Act,%201976.pdf",
    "https://drs.molaw.gov.pk/pdf/XXVII-%20The%20Employees%E2%80%99%20Old-Age%20Benefits%20Ordinance,%201975_1.pdf",
    "https://drs.molaw.gov.pk/pdf/XXVIII.%20%20The%20Dock%20Workers%20(Regulation%20of%20Employment)%20Ordinance,%201973..pdf",
    "https://drs.molaw.gov.pk/pdf/XXII%20%20%20The%20Employees'%20Cost%20of%20Living%20(Relief)%20Ordinance,%201973.pdf",
    "https://drs.molaw.gov.pk/pdf/XV%20%20The%20Service%20Tribunals%20Ordinance,%201973.pdf",
    "https://drs.molaw.gov.pk/pdf/CXVI-%20The%20Removal%20From%20Service%20(Review%20Petition)%20Regulation,%201972.pdf",
    "https://drs.molaw.gov.pk/pdf/XXXVI-%20The%20Workers%E2%80%99%20Welfare%20Fund%20Ordinance,%201971.pdf",
    "https://drs.molaw.gov.pk/pdf/XXIII-%20The%20Industrial%20Relations%20Ordinance,%201969.pdf",
    "https://drs.molaw.gov.pk/pdf/The%20West%20Pakistan%20Minimum%20Wages%20for%20Unskilled%20Workers%20Ordinance,%201969.pdf",
    "https://drs.molaw.gov.pk/pdf/XII-%20The%20Companies%20Profits%20(Workers%20Participation)%20Act,%201968.pdf",
    "https://drs.molaw.gov.pk/pdf/XXVI-%20The%20Labour%20Laws%20(Amendment)%20Ordinance,%201975.pdf",
    "https://drs.molaw.gov.pk/pdf/XXXII-%20The%20Control%20of%20Employment%20Ordinance,%201965.pdf",
    "https://drs.molaw.gov.pk/pdf/LVI.%20The%20Apprenticeship%20Ordinance,%201962.pdf",
    "https://drs.molaw.gov.pk/pdf/XXXIX%20The%20Minimum%20Wages%20Ordinance,%201961.pdf",
    "https://drs.molaw.gov.pk/pdf/XXVIII%20The%20Road%20Transport%20Workers%20Ordinance,%201961.pdf",
    "https://drs.molaw.gov.pk/pdf/XXXIX%20The%20Coal%20Mines%20(Fixation%20of%20Rates%20of%20Wages)%20Ordinance,%201960.pdf",
    "https://drs.molaw.gov.pk/pdf/III%20The%20Industrial%20and%20Commercial%20Employment%20(Standing%20Orders)%20Ordinance,%201960.pdf",
    "https://drs.molaw.gov.pk/pdf/XVI%20The%20Working%20Journalists%20(Conditions%20of%20Service)%20Ordinance,%201960.pdf",
    "https://drs.molaw.gov.pk/pdf/LVI%20The%20Industrial%20Disputes%20Ordinance,%201959.pdf",
    "https://drs.molaw.gov.pk/pdf/XXXII-%20THe%20West%20Pakistan%20Maternity%20Benefit%20Ordinance,%201958(1).pdf",
    "https://drs.molaw.gov.pk/pdf/XII%20The%20Communication%20and%20Transport%20Services%20Maintenance%20Ordinance,%201957.pdf",
]

os.makedirs("data/raw_pdfs", exist_ok=True)

for url in PDF_URLS:
    filename = url.split("/")[-1]
    filepath = f"data/raw_pdfs/{filename}"
    if os.path.exists(filepath):
        print(f"Already exists: {filename}")
        continue
    try:
        response = requests.get(url, timeout=30)
        with open(filepath, "wb") as f:
            f.write(response.content)
        print(f"Downloaded: {filename}")
        time.sleep(1)  # be polite to the server
    except Exception as e:
        print(f"Failed: {filename} — {e}")