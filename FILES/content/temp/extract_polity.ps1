# Extract remaining Polity sources
python content/scripts/extract_pdf.py "content/sources/Laxmikanth-Indian-Polity-8th-Ed.pdf" --pages 130-180 -o content/temp/polity-laxmikanth-parliament.txt
python content/scripts/extract_pdf.py "content/sources/Laxmikanth-Indian-Polity-8th-Ed.pdf" --pages 250-300 -o content/temp/polity-laxmikanth-judiciary.txt
python content/scripts/extract_pdf.py "content/sources/Laxmikanth-Indian-Polity-8th-Ed.pdf" --pages 350-400 -o content/temp/polity-laxmikanth-federalism.txt
python content/scripts/extract_pdf.py "content/sources/Laxmikanth-Indian-Polity-8th-Ed.pdf" --pages 500-550 -o content/temp/polity-laxmikanth-local-govt.txt
python content/scripts/extract_pdf.py "content/sources/NCERT-Class11-PolSci-Indian-Constitution-at-Work.pdf" --all -o content/temp/polity-ncert11.txt
python content/scripts/extract_pdf.py "content/sources/NCERT-Class-12-Political-Science-Part-1.pdf" --all -o content/temp/polity-ncert12-p1.txt
python content/scripts/extract_pdf.py "content/sources/NCERT-Class-12-Political-Science-Part-2.pdf" --all -o content/temp/polity-ncert12-p2.txt
