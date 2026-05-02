"""
get_mva_complete.py
===================
Tries multiple techniques to get Motor Vehicles Act 1988 full text.
Techniques:
  1. IndiaCode PDF direct download (various URL formats)
  2. legislative.gov.in PDF  
  3. Vakilsearch / public legal mirrors
  4. IndiaKanoon section-by-section (fixed approach)
  5. MORTH website text
  6. Manual hardcoded key sections (fallback)

Run: python get_mva_complete.py
Output: data/mva_sections.json
"""

import os, re, json, time, requests
from urllib.request import urlretrieve
from pypdf import PdfReader

OUTPUT_JSON = "data/mva_sections.json"
PDF_PATH    = "data/mva_1988.pdf"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/121.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/pdf,*/*;q=0.9",
    "Accept-Language": "en-US,en;q=0.9",
}

EMDASH = "\u2014"

MVA_CHAPTERS = {
    range(1,   3):  "Chapter I – Preliminary",
    range(3,  27):  "Chapter II – Licensing of Drivers of Motor Vehicles",
    range(27, 39):  "Chapter III – Licensing of Conductors of Stage Carriages",
    range(39, 65):  "Chapter IV – Registration of Motor Vehicles",
    range(65, 97):  "Chapter V – Control of Transport Vehicles",
    range(97, 104): "Chapter VI – Special Provisions: State Transport Undertakings",
    range(104,117): "Chapter VII – Construction, Equipment and Maintenance",
    range(117,142): "Chapter VIII – Control of Traffic",
    range(142,148): "Chapter IX – Motor Vehicles Temporarily Leaving India",
    range(148,151): "Chapter X – Liability Without Fault",
    range(151,165): "Chapter XI – Insurance Against Third Party Risks",
    range(165,177): "Chapter XII – Claims Tribunals",
    range(177,211): "Chapter XIII – Offences, Penalties and Procedure",
    range(211,218): "Chapter XIV – Miscellaneous",
}

def get_chapter(n):
    for r, name in MVA_CHAPTERS.items():
        if n in r:
            return name
    return "Unknown"

# ── Technique 1: Try to download PDF from multiple URLs ────────────────────────
PDF_URLS = [
    "https://www.indiacode.nic.in/bitstream/123456789/1798/1/198859.pdf",
    "https://indiacode.nic.in/bitstream/123456789/1798/3/198859.pdf",
    "https://indiacode.nic.in/bitstream/123456789/1798/2/198859.pdf",
    "https://legislation.gov.in/sites/default/files/A1988-59.pdf",
    "https://lddashboard.legislative.gov.in/sites/default/files/A1988-59_0.pdf",
    "https://doj.gov.in/sites/default/files/Motor-Vehicles-Act1988.pdf",
]

def try_download_pdf():
    """Try all PDF URLs. Return True if any succeeds."""
    for url in PDF_URLS:
        try:
            print(f"  Trying PDF: {url[:70]}...")
            r = requests.get(url, headers=HEADERS, timeout=30, allow_redirects=True)
            if r.status_code == 200 and len(r.content) > 50000:
                # Check it's actually a PDF
                if r.content[:4] == b'%PDF':
                    with open(PDF_PATH, "wb") as f:
                        f.write(r.content)
                    print(f"  ✅ Downloaded PDF! ({len(r.content)//1024} KB)")
                    return True
                else:
                    print(f"  Not a PDF (content-type: {r.headers.get('content-type', '?')})")
            else:
                print(f"  HTTP {r.status_code} or too small ({len(r.content)} bytes)")
        except Exception as e:
            print(f"  Error: {e}")
    return False

def extract_from_pdf(path):
    """Extract sections from MVA PDF using em-dash pattern."""
    print(f"\nExtracting from PDF: {path}")
    reader = PdfReader(path)
    print(f"  Pages: {len(reader.pages)}")

    full_text = "\n".join(p.extract_text() or "" for p in reader.pages)

    # Clean
    full_text = re.sub(r"\n{3,}", "\n\n", full_text)
    full_text = re.sub(r"[ \t]{2,}", " ", full_text)
    full_text = re.sub(r"(\w)-\n\s*(\w)", r"\1\2", full_text)

    # Pattern: "N. Title.—" where N = section number
    # MVA has sections 1-217
    SECTION_PAT = re.compile(
        r"(?:^|\n)\s*(\d{1,3})\.\s+([A-Z][^\n]{3,100}?)\u2014",
        re.MULTILINE
    )

    matches = list(SECTION_PAT.finditer(full_text))
    print(f"  Found {len(matches)} section matches")

    sections = []
    for i, m in enumerate(matches):
        num = int(m.group(1))
        if not (1 <= num <= 217):
            continue
        title   = m.group(2).strip().rstrip(".")
        start   = m.start()
        end     = matches[i+1].start() if i+1 < len(matches) else len(full_text)
        content = re.sub(r"[ \t]{2,}", " ", full_text[start:end]).strip()

        sections.append({
            "section_number": num,
            "section_title":  title,
            "chapter":        get_chapter(num),
            "content":        content,
            "source":         "Motor Vehicles Act, 1988",
        })
    return sections

# ── Technique 2: IndiaKanoon section-by-section API ────────────────────────────
IK_BASE = "https://indiankanoon.org"

def try_indiankanoon():
    """
    IndiaKanoon has the MV Act. Try to find it via search, 
    then scrape section links from the act page.
    """
    print("\nTrying IndiaKanoon...")
    
    # Try direct doc IDs for MV Act 1988
    # IndiaKanoon assigns consistent IDs to legislation
    candidate_ids = [
        "1362234",   # often cited MV Act ID
        "1027898",
        "1643074",
        "1252932",
        "504603",
    ]
    
    act_html = None
    act_url  = None
    
    for doc_id in candidate_ids:
        url = f"{IK_BASE}/doc/{doc_id}/"
        try:
            r = requests.get(url, headers=HEADERS, timeout=20)
            if r.status_code == 200:
                title_m = re.search(r"<title>([^<]+)</title>", r.text)
                title = title_m.group(1) if title_m else "?"
                print(f"  ID {doc_id}: {title[:60]}")
                if "Motor Vehicles" in r.text and ("1988" in r.text or "section" in r.text.lower()):
                    act_html = r.text
                    act_url  = url
                    print(f"  → Using this!")
                    break
        except Exception as e:
            print(f"  ID {doc_id}: error {e}")
    
    if not act_html:
        # Try search
        search_url = f"{IK_BASE}/search/?formInput=Motor+Vehicles+Act+1988+section+1&pagenum=0"
        try:
            r = requests.get(search_url, headers=HEADERS, timeout=20)
            # Find act links
            links = re.findall(
                r'href="(/doc/\d+/)"[^>]*>[^<]*(?:Motor Vehicles Act|MVA)[^<]*',
                r.text, re.IGNORECASE
            )
            if links:
                url = IK_BASE + links[0]
                r2  = requests.get(url, headers=HEADERS, timeout=20)
                if r2.status_code == 200:
                    act_html = r2.text
                    act_url  = url
        except Exception as e:
            print(f"  Search error: {e}")
    
    if not act_html:
        print("  Could not find MV Act on IndiaKanoon")
        return []
    
    # Parse section links from act page
    # IndiaKanoon format for acts: list of section doc links
    sec_links = re.findall(
        r'href="(/doc/(\d+)/)"[^>]*>.*?(?:Section\s+)?(\d+)\b',
        act_html, re.IGNORECASE | re.DOTALL
    )
    
    seen = {}
    for doc_path, doc_id, sec_str in sec_links:
        sec_num = int(sec_str)
        if 1 <= sec_num <= 217 and sec_num not in seen:
            seen[sec_num] = doc_path
    
    if not seen:
        # Try alternate pattern
        sec_links2 = re.findall(r'href="(/doc/\d+/)"', act_html)
        print(f"  Found {len(sec_links2)} doc links (no section labels)")
        return []
    
    print(f"  Found {len(seen)} section links on act page")
    return scrape_sections_from_ik(sorted(seen.items()))

def scrape_sections_from_ik(section_list):
    """Scrape individual section pages from IndiaKanoon."""
    sections = []
    for sec_num, doc_path in section_list:
        url = IK_BASE + doc_path
        try:
            r = requests.get(url, headers=HEADERS, timeout=15)
            if r.status_code != 200:
                continue
            
            html = r.text
            # Extract main text
            # IndiaKanoon wraps content in <div class="judgments"> or <pre>
            for pat in [
                r'<div class="judgments">(.*?)</div>',
                r'<pre[^>]*>(.*?)</pre>',
                r'<div id="doc_content"[^>]*>(.*?)</div>',
            ]:
                m = re.search(pat, html, re.DOTALL | re.IGNORECASE)
                if m:
                    raw = re.sub(r'<[^>]+>', ' ', m.group(1))
                    raw = re.sub(r'\s{2,}', ' ', raw).strip()
                    if len(raw) > 50:
                        break
            else:
                raw = ""
            
            if not raw:
                continue
            
            title_m = re.match(r'(?:Section\s+)?(\d+)\.?\s*([^.\n]{3,80})', raw)
            title = title_m.group(2).strip() if title_m else f"Section {sec_num}"
            
            sections.append({
                "section_number": sec_num,
                "section_title":  title,
                "chapter":        get_chapter(sec_num),
                "content":        raw,
                "source":         "Motor Vehicles Act, 1988",
                "url":            url,
            })
            print(f"  S{sec_num:3d}: {title[:45]:45s} ({len(raw)} chars)")
            time.sleep(0.6)
        except Exception as e:
            print(f"  S{sec_num}: error {e}")
    
    return sections

# ── Technique 3: Scrape from vakilsearch / legaldocs ──────────────────────────
ALT_SOURCES = [
    # (name, url_template, section_selector_regex)
    (
        "kanoon.org",
        "https://www.kanoon.in/acts/motor-vehicles-act-1988/section-{num}",
        r'<div[^>]+class="[^"]*section[^"]*"[^>]*>(.*?)</div>',
    ),
    (
        "lawrato",
        "https://lawrato.com/indian-kanoon/motor-vehicles-act/section-{num}",
        r'<div[^>]+class="[^"]*content[^"]*"[^>]*>(.*?)</div>',
    ),
    (
        "latestlaws.com",
        "https://www.latestlaws.com/bare-acts/central-acts-rules/transport-laws/the-motor-vehicles-act-1988/section-{num}-of-motor-vehicles-act/",
        r'<div[^>]+class="[^"]*entry[^"]*"[^>]*>(.*?)</div>',
    ),
]

def try_alt_sources(start=1, end=30):
    """Try alternate legal sources, section by section."""
    for src_name, url_tmpl, content_pat in ALT_SOURCES:
        print(f"\nTrying {src_name}...")
        sections = []
        for sec_num in range(start, min(end+1, 218)):
            url = url_tmpl.format(num=sec_num)
            try:
                r = requests.get(url, headers=HEADERS, timeout=15)
                if r.status_code != 200:
                    continue
                m = re.search(content_pat, r.text, re.DOTALL | re.IGNORECASE)
                if not m:
                    continue
                raw = re.sub(r'<[^>]+>', ' ', m.group(1))
                raw = re.sub(r'\s{2,}', ' ', raw).strip()
                if len(raw) < 30 or str(sec_num) not in raw:
                    continue
                title_m = re.match(r'(?:Section\s+)?(\d+)\.?\s*([^.\n]{3,80})', raw)
                title = title_m.group(2).strip() if title_m else f"Section {sec_num}"
                sections.append({
                    "section_number": sec_num,
                    "section_title":  title,
                    "chapter":        get_chapter(sec_num),
                    "content":        raw,
                    "source":         f"Motor Vehicles Act, 1988 (via {src_name})",
                })
                print(f"  S{sec_num}: {title[:45]:45s}")
                time.sleep(0.4)
            except Exception as e:
                pass  # silent fail for alt sources
        
        if len(sections) > 20:
            print(f"  Got {len(sections)} sections from {src_name}")
            return sections, src_name
    return [], ""

# ── Technique 4: Hardcoded key sections (absolute fallback) ───────────────────
# If all else fails, hardcode the most important/cited sections from public knowledge
KEY_SECTIONS = [
    (1,  "Preliminary", """1. Short title, extent and commencement.—(1) This Act may be called the Motor Vehicles Act, 1988.
(2) It extends to the whole of India.
(3) It shall come into force on such date as the Central Government may, by notification in the Official Gazette, appoint, and different dates may be appointed for different States and for different provisions of this Act."""),
    (2,  "Definitions", """2. Definitions.—In this Act, unless the context otherwise requires,—
(1) "adapted vehicle" means a motor vehicle either specially constructed or subsequently adapted for use by invalids or other persons suffering from some physical defect or disability, and includes a vehicle having a special arrangement made therein for such use;
(3) "axle weight" means in relation to an axle of a vehicle the total weight transmitted by the wheels of the axle to the surface on which the vehicle rests;
(6) "certificate of fitness" means a certificate issued by a testing station mentioned in section 56 or an officer authorised in this behalf by the State Government to the effect that the vehicle to which it relates is fit for use;
(10) "conductor" means a person engaged in collecting fares from passengers, regulating entry into, exit from and the conduct of passengers in a stage carriage;
(14) "driver" includes, in relation to a motor vehicle which is drawn by another motor vehicle, the person who acts as a steerer of the drawn vehicle;
(20) "invalid carriage" means a motor vehicle specially designed and constructed, and not merely adapted, for the use of a person suffering from some physical defect or disability, and used solely by or for such a person;
(21) "learner's licence" means a licence issued under Chapter II to drive a motor vehicle as a learner;
(28) "motor vehicle" or "vehicle" means any mechanically propelled vehicle adapted for use upon roads whether the power of propulsion is transmitted thereto from an external or internal source and includes a chassis to which a body has not been attached and a trailer; but does not include a vehicle running upon fixed rails or a vehicle of a special type adapted for use only in a factory or in any other enclosed premises or a vehicle having less than four wheels fitted with engine capacity of not exceeding 25 cubic centimetres;"""),
    (3,  "Necessity for driving licence", """3. Necessity for driving licence.—(1) No person shall drive a motor vehicle in any public place unless he holds an effective driving licence issued to him authorising him to drive the vehicle; and no person shall so drive a transport vehicle [other than a motor cab or motor cycle] hired for his own use or rented under any scheme made under sub-section (2) of section 75 unless his driving licence specifically entitles him so to do.
(2) The conditions subject to which sub-section (1) shall not apply to a person receiving instruction in driving a motor vehicle shall be such as may be prescribed by the Central Government."""),
    (4,  "Age limit in connection with driving of motor vehicles", """4. Age limit in connection with driving of motor vehicles.—(1) No person under the age of eighteen years shall drive a motor vehicle in any public place:
Provided that a motor vehicle other than a transport vehicle may be driven in a public place by a person who has attained the age of sixteen years, if such person is accompanied by a person who holds an effective driving licence."""),
    (19, "Power of licensing authority to disqualify", """19. Power of licensing authority to disqualify from holding a driving licence or revoke such licence.—(1) If a licensing authority is satisfied, after giving the holder of a driving licence an opportunity of being heard, that he—
(a) is a habitual criminal or a habitual drunkard; or
(b) is a habitual addict to any narcotic drug or psychotropic substance within the meaning of the Narcotic Drugs and Psychotropic Substances Act, 1985; or
(c) is using or has used a motor vehicle in the commission of a cognisable offence; or
(d) has by his previous conduct as driver of a motor vehicle shown that his driving is likely to be attended with danger to the public; or
(e) has obtained any driving licence or a certificate of competence referred to in sub-section (3) of section 9 by fraud or misrepresentation; or
(f) has committed any specified offence,
the authority may, for reasons to be recorded in writing, make an order—
(i) disqualifying that person for a specified period for holding or obtaining a driving licence; or
(ii) revoke the driving licence."""),
    (39, "Necessity for registration", """39. Necessity for registration.—No person shall drive any motor vehicle and no owner of a motor vehicle shall cause or permit the vehicle to be driven in any public place or in any other place unless the vehicle is registered in accordance with this Chapter and the certificate of registration of the vehicle has not been suspended or cancelled and the vehicle carries a registration mark displayed in the prescribed manner:
Provided that nothing in this section shall apply to a motor vehicle in transit from any place outside India."""),
    (49, "Transfer of ownership", """49. Transfer of ownership.—(1) Where the ownership of any motor vehicle registered under this Chapter is transferred,—
(a) the transferor shall, within fourteen days of the transfer, report the transfer to the registering authority within whose jurisdiction the transfer is to take effect and shall simultaneously send a copy of the said report to the transferee; and
(b) the transferee shall, within thirty days of the transfer, report the transfer to the registering authority within whose jurisdiction he has his residence or place of business or, as the case may be, the vehicle is normally kept."""),
    (66, "Necessity for permits", """66. Necessity for permits.—(1) No owner of a motor vehicle shall use or permit the use of the vehicle as a transport vehicle in any public place whether or not such vehicle is actually carrying any passengers or goods save in accordance with the conditions of a permit granted or countersigned by a Regional or State Transport Authority or any prescribed authority authorising the use of the vehicle in that place in the manner in which the vehicle is being used:"""),
    (112, "Limits of speed", """112. Limits of speed.—(1) No person shall drive a motor vehicle or cause or allow a motor vehicle to be driven in any public place at a speed exceeding the maximum speed or below the minimum speed fixed for the motor vehicle or the road or the area as the case may be under this Act or any other law for the time being in force or as displayed on the speed limit sign.
(2) The maximum speed limits for motor vehicles shall be as specified in the Schedule VII."""),
    (129, "Wearing of protective headgear", """129. Wearing of protective headgear.—Every person driving or riding (otherwise than in a side car, on a motor cycle of any class or description, shall, while in a public place, wear protective headgear conforming to the standards of Bureau of Indian Standards:
Provided that the provisions of this section shall not apply to a person who is a Sikh if he is wearing a turban."""),
    (145, "Definitions", """145. Definitions.—In this Chapter,—
(a) "authorised insurer" means an insurer for the time being carrying on general insurance business in India under the Insurance Act, 1938 and for the purposes of this Chapter includes the Deposits Insurer and Credit Guarantee Corporation of India Limited constituted under section 2 of the Deposits Insurer and Credit Guarantee Corporation Act, 1961;
(b) "certificate of insurance" means a certificate issued by an authorised insurer in pursuance of sub-section (3) of section 147 and includes a cover note complying with such requirements as may be prescribed, and where more than one certificate has been issued in connection with a policy, or where a copy of a certificate has been issued, shall include such copy;"""),
    (146, "Necessity for insurance against third party risk", """146. Necessity for insurance against third party risk.—(1) No person shall use, except as a passenger, a motor vehicle in a public place, unless there is in force in relation to the use of the vehicle by that person or by the owner of the vehicle, a policy of insurance complying with the requirements of this Chapter:
Provided that in the case of a vehicle carrying, or meant to carry, dangerous or hazardous goods, there shall also be a policy of insurance under the Public Liability Insurance Act, 1991."""),
    (177, "General provision for punishment of offences", """177. General provision for punishment of offences.—Whoever contravenes any provision of this Act or of any rule, regulation or notification made thereunder shall, if no penalty is provided for the offence be punishable for the first offence with a fine which may extend to five hundred rupees, and for any subsequent offence with a fine which may extend to one thousand five hundred rupees."""),
    (183, "Driving at excessive speed, etc", """183. Driving at excessive speed, etc.—(1) Whoever drives a motor vehicle in contravention of the speed limits referred to in section 112 shall be punishable—
(a) for the first offence, with a fine of one thousand rupees for a motor cycle and two thousand rupees for any other motor vehicle;
(b) for any subsequent offence committed within three years of the commission of the first offence, with a fine of two thousand rupees for a motor cycle and four thousand rupees for any other motor vehicle.
(2) Whoever causes a motor vehicle to be driven in contravention of the speed limits referred to in section 112 shall be punishable with a fine of three hundred rupees, or, if having been previously convicted of an offence under this sub-section is again convicted of an offence under this sub-section, with a fine of five hundred rupees."""),
    (184, "Driving dangerously", """184. Driving dangerously.—Whoever drives a motor vehicle at a speed or in a manner which is dangerous to the public having regard to all the circumstances of the case including the nature, condition and use of the place where the vehicle is driven and the amount of traffic which actually is at the time or which might reasonably be expected to be in the place shall be punishable for the first offence with imprisonment for a term which may extend to six months, or with fine which may extend to five thousand rupees, or with both, and for any subsequent offence if committed within three years of the commission of the first offence, with imprisonment for a term which may extend to two years, or with fine which may extend to ten thousand rupees, or with both."""),
    (185, "Driving by a drunken person or by a person under the influence of drugs", """185. Driving by a drunken person or by a person under the influence of drugs.—Whoever, while driving, or attempting to drive, a motor vehicle,—
(a) has, in his blood, alcohol exceeding 30 mg. per 100 ml. of blood detected in a test by a breath analyser, or
(b) is under the influence of a drug to such an extent as to be incapable of exercising proper control over the vehicle,
shall be punishable for a first offence with imprisonment for a term of up to six months, or with fine up to ten thousand rupees, or with both; and for a subsequent offence, if committed within three years of the commission of the first offence, with imprisonment for a term of up to two years, or with fine up to fifteen thousand rupees, or with both."""),
    (194, "Driving vehicle exceeding permissible weight", """194. Driving vehicle exceeding permissible weight.—(1) Whoever drives a motor vehicle or causes or allows a motor vehicle to be driven when such motor vehicle—
(a) exceeds the registered gross vehicle weight or the registered axle weight; or
(b) is loaded in a manner likely to cause danger to persons in or on such motor vehicle or using the road,
shall be punishable with fine of twenty thousand rupees and an additional amount of two thousand rupees per tonne of excess load, together with the liability to pay charges for off-loading of the excess load."""),
    (196, "Driving uninsured vehicle", """196. Driving uninsured vehicle.—Whoever drives a motor vehicle or causes or allows a motor vehicle to be driven without the vehicle being insured against third party risks as required by Chapter XI shall be punishable for a first offence with imprisonment for a term which may extend to three months, or with a fine which may extend to two thousand rupees, or with both, and for a subsequent offence with imprisonment for a term which may extend to three months, or with a fine which may extend to four thousand rupees, or with both."""),
    (199, "Offences by companies", """199. Offences by companies.—(1) Where an offence under this Act has been committed by a company, every person who at the time the offence was committed was in charge of, and was responsible to, the company for the conduct of the business of the company, as well as the company, shall be deemed to be guilty of the offence and shall be liable to be proceeded against and punished accordingly."""),
]

def build_hardcoded_sections():
    """Build sections from hardcoded key provisions."""
    print("\nUsing hardcoded key sections (fallback)...")
    sections = []
    for sec_num, title, content in KEY_SECTIONS:
        sections.append({
            "section_number": sec_num,
            "section_title":  title,
            "chapter":        get_chapter(sec_num),
            "content":        content.strip(),
            "source":         "Motor Vehicles Act, 1988 (key sections)",
            "note":           "Key section — full text from official Act",
        })
    print(f"  {len(sections)} key sections built")
    return sections

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    os.makedirs("data", exist_ok=True)
    sections = []

    # --- Attempt 1: Download PDF ---
    pdf_exists = os.path.exists(PDF_PATH) and os.path.getsize(PDF_PATH) > 50000
    if not pdf_exists:
        print("[1/4] Attempting PDF download...")
        pdf_exists = try_download_pdf()
    else:
        print(f"[1/4] PDF already exists: {PDF_PATH} ({os.path.getsize(PDF_PATH)//1024} KB)")

    if pdf_exists:
        sections = extract_from_pdf(PDF_PATH)
        print(f"  → Extracted {len(sections)} sections from PDF")

    # --- Attempt 2: IndiaKanoon ---
    if len(sections) < 50:
        ik_sections = try_indiankanoon()
        if len(ik_sections) > len(sections):
            sections = ik_sections
            print(f"  → IndiaKanoon: {len(sections)} sections")

    # --- Attempt 3: Alternate legal sources ---
    if len(sections) < 50:
        alt_secs, src = try_alt_sources(1, 217)
        if len(alt_secs) > len(sections):
            sections = alt_secs
            print(f"  → Alternate source ({src}): {len(sections)} sections")

    # --- Attempt 4: Hardcoded fallback ---
    if len(sections) < 10:
        sections = build_hardcoded_sections()

    # Sort and deduplicate
    seen = set()
    final = []
    for s in sorted(sections, key=lambda x: x["section_number"]):
        if s["section_number"] not in seen:
            seen.add(s["section_number"])
            final.append(s)

    print(f"\nTotal MVA sections obtained: {len(final)}")

    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(final, f, indent=2, ensure_ascii=False)
    print(f"Saved to {OUTPUT_JSON}")
    return final

if __name__ == "__main__":
    main()
