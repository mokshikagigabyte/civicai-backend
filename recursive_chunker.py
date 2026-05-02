"""
recursive_chunker.py
====================
Applies Recursive Text Splitting (LangChain RecursiveCharacterTextSplitter style)
to motor_vehicles_db.json.

Algorithm:
  - Split text using a priority list of separators:
      ["\n\n", "\n", ". ", "; ", ", ", " ", ""]
  - If a piece still exceeds chunk_size, recurse with next separator
  - Keep overlap between consecutive chunks (100 chars default)
  - Never cross rule/section boundaries

Output: D:\moptor_vehical_dataset\motor_vehicles_rag_recursive.json
"""

import json, re, os

# ── Config ───────────────────────────────────────────────────────────────────
DB_PATH   = r"D:\moptor_vehical_dataset\motor_vehicles_db.json"
OUT_PATH  = r"D:\moptor_vehical_dataset\motor_vehicles_rag_recursive.json"

CHUNK_SIZE    = 800   # target tokens per chunk (approx 4 chars = 1 token)
CHUNK_OVERLAP = 100   # overlap tokens between chunks
CHARS_PER_TOK = 4

CHUNK_CHARS   = CHUNK_SIZE    * CHARS_PER_TOK   # 3200 chars
OVERLAP_CHARS = CHUNK_OVERLAP * CHARS_PER_TOK   # 400 chars

# Separator hierarchy (most preferred → least preferred)
SEPARATORS = ["\n\n", "\n", ". ", "; ", ", ", " ", ""]

# ── MVA chapter lookup ────────────────────────────────────────────────────────
MVA_CHAPTERS = {
    range(1,3):    "Chapter I – Preliminary",
    range(3,27):   "Chapter II – Licensing of Drivers",
    range(27,39):  "Chapter III – Licensing of Conductors",
    range(39,65):  "Chapter IV – Registration of Motor Vehicles",
    range(65,97):  "Chapter V – Control of Transport Vehicles",
    range(97,104): "Chapter VI – State Transport Undertakings",
    range(104,117):"Chapter VII – Construction & Equipment",
    range(117,142):"Chapter VIII – Control of Traffic",
    range(142,148):"Chapter IX – Vehicles Leaving India",
    range(148,151):"Chapter X – Liability Without Fault",
    range(151,165):"Chapter XI – Insurance Third Party",
    range(165,177):"Chapter XII – Claims Tribunals",
    range(177,211):"Chapter XIII – Offences & Penalties",
    range(211,218):"Chapter XIV – Miscellaneous",
}

CMVR_CHAPTERS = {
    0: "Appendices, Orders and Regulations",
    1: "Chapter I – Preliminary",
    2: "Chapter II – Licensing of Drivers",
    3: "Chapter III – Registration of Motor Vehicles",
    4: "Chapter IV – Control of Transport Vehicles",
    5: "Chapter V – Construction, Equipment and Maintenance",
    6: "Chapter VI – State Transport Undertakings",
    7: "Chapter VII – Insurance Against Third Party Risks",
}

def get_mva_chapter(n):
    try:
        n = int(re.sub(r"[A-Za-z]", "", str(n)))
    except Exception:
        return "Unknown Chapter"
    for r, c in MVA_CHAPTERS.items():
        if n in r: return c
    return "Unknown Chapter"

# ── Core: Recursive Text Splitter ────────────────────────────────────────────
def _split_text(text: str, separators: list, chunk_size: int) -> list:
    """
    Recursively split text using the first separator that produces
    pieces small enough. If pieces are still too large, recurse.
    """
    # Find the best separator that exists in text
    sep = ""
    remaining_seps = []
    for i, s in enumerate(separators):
        if s == "" or s in text:
            sep = s
            remaining_seps = separators[i+1:]
            break

    # Split on chosen separator
    if sep == "":
        splits = list(text)  # character-level last resort
    else:
        splits = text.split(sep)

    # Re-join small splits to approach chunk_size, recurse on large ones
    good_splits = []
    current = []
    current_len = 0

    for piece in splits:
        piece_len = len(piece)

        if piece_len > chunk_size:
            # This piece itself is too big — recurse
            if current:
                merged = sep.join(current).strip()
                if merged:
                    good_splits.append(merged)
                current = []
                current_len = 0
            sub_splits = _split_text(piece, remaining_seps, chunk_size)
            good_splits.extend(sub_splits)
        elif current_len + len(sep) + piece_len > chunk_size:
            # Adding this piece would overflow — flush current
            if current:
                merged = sep.join(current).strip()
                if merged:
                    good_splits.append(merged)
            current = [piece]
            current_len = piece_len
        else:
            current.append(piece)
            current_len += len(sep) + piece_len

    if current:
        merged = sep.join(current).strip()
        if merged:
            good_splits.append(merged)

    return good_splits

def recursive_split(text: str,
                    chunk_size: int = CHUNK_CHARS,
                    chunk_overlap: int = OVERLAP_CHARS,
                    separators: list = None) -> list:
    """
    Main entry point. Returns list of text chunks with overlap.
    """
    if separators is None:
        separators = SEPARATORS

    text = re.sub(r"[ \t]{2,}", " ", text.strip())
    text = re.sub(r"\n{3,}", "\n\n", text)

    if len(text) <= chunk_size:
        return [text] if text.strip() else []

    raw_splits = _split_text(text, separators, chunk_size)

    # Apply overlap: merge consecutive splits adding overlap from previous
    final_chunks = []
    for i, split in enumerate(raw_splits):
        if i == 0:
            final_chunks.append(split)
        else:
            # Take last overlap_chars from previous chunk as prefix
            prev = final_chunks[-1]
            overlap_text = prev[-chunk_overlap:].strip() if len(prev) > chunk_overlap else prev.strip()
            # Only add overlap if it doesn't repeat the start of current split
            if not split.startswith(overlap_text[:30]):
                chunk_with_overlap = overlap_text + " " + split
            else:
                chunk_with_overlap = split
            final_chunks.append(chunk_with_overlap.strip())

    return [c for c in final_chunks if c.strip()]

# ── Build chunks from source ──────────────────────────────────────────────────
def build_chunk_record(idx, text, section_id, section_number,
                        section_title, act_name, metadata,
                        total_chunks):
    return {
        "act_name":       act_name,
        "section_number": str(section_number),
        "section_title":  section_title,
        "chunk_id":       f"{section_id}_chunk_{idx+1}",
        "chunk_text":     text.strip(),
        "token_estimate": len(text) // CHARS_PER_TOK,
        "metadata":       dict(metadata,
                               chunk_index=idx+1,
                               total_chunks=total_chunks,
                               splitter="RecursiveTextSplitter",
                               chunk_size_tokens=CHUNK_SIZE,
                               chunk_overlap_tokens=CHUNK_OVERLAP),
    }

def process_section(section_number, section_title, content,
                    act_name, section_key, metadata):
    if not content or not content.strip():
        return []
    chunks = recursive_split(content)
    total  = len(chunks)
    return [
        build_chunk_record(i, c, section_key, section_number,
                           section_title, act_name, metadata, total)
        for i, c in enumerate(chunks)
    ]

# ── MVA 1988 hardcoded sections ───────────────────────────────────────────────
MVA_SECTIONS = [
{"n": 1, "t": "Short title, extent and commencement", "c": """1. Short title, extent and commencement.—(1) This Act may be called the Motor Vehicles Act, 1988. (2) It extends to the whole of India. (3) It shall come into force on such date as the Central Government may, by notification in the Official Gazette, appoint, and different dates may be appointed for different States and for different provisions of this Act."""},
{"n": 2, "t": "Definitions", "c": """2. Definitions.—In this Act, unless the context otherwise requires,— (1) "adapted vehicle" means a motor vehicle either specially constructed or subsequently adapted for use by invalids or other persons suffering from some physical defect or disability; (3) "axle weight" means the total weight transmitted by the wheels of the axle to the surface on which the vehicle rests; (6) "certificate of fitness" means a certificate issued by a testing station or officer authorised by the State Government to the effect that the vehicle is fit for use; (10) "conductor" means a person engaged in collecting fares from passengers, regulating entry into, exit from and the conduct of passengers in a stage carriage; (14) "driver" includes, in relation to a motor vehicle which is drawn by another motor vehicle, the person who acts as a steerer of the drawn vehicle; (20) "invalid carriage" means a motor vehicle specially designed and constructed for the use of a person suffering from some physical defect or disability; (21) "learner's licence" means a licence issued under Chapter II to drive a motor vehicle as a learner; (28) "motor vehicle" or "vehicle" means any mechanically propelled vehicle adapted for use upon roads whether the power of propulsion is transmitted thereto from an external or internal source and includes a chassis to which a body has not been attached and a trailer; but does not include a vehicle running upon fixed rails or a vehicle of a special type adapted for use only in a factory or in any other enclosed premises or a vehicle having less than four wheels fitted with engine capacity of not exceeding 25 cubic centimetres; (29) "omnibus" means a motor vehicle constructed or adapted to carry more than six persons excluding the driver; (30) "owner" means a person in whose name a motor vehicle stands registered; (34) "permit" means a permit issued under this Act; (40) "public place" means a road, street, way or other place to which the public have a right of access; (47) "stage carriage" means a motor vehicle constructed to carry more than six persons excluding driver and used for carrying passengers for hire or reward at separate fares."""},
{"n": 3, "t": "Necessity for driving licence", "c": """3. Necessity for driving licence.—(1) No person shall drive a motor vehicle in any public place unless he holds an effective driving licence issued to him authorising him to drive the vehicle; and no person shall so drive a transport vehicle unless his driving licence specifically entitles him so to do. (2) The conditions subject to which sub-section (1) shall not apply to a person receiving instruction in driving a motor vehicle shall be such as may be prescribed by the Central Government."""},
{"n": 4, "t": "Age limit in connection with driving of motor vehicles", "c": """4. Age limit in connection with driving of motor vehicles.—(1) No person under the age of eighteen years shall drive a motor vehicle in any public place: Provided that a motor vehicle other than a transport vehicle may be driven in a public place by a person who has attained the age of sixteen years, if such person is accompanied by a person who holds an effective driving licence. (2) No person under the age of twenty years shall drive a transport vehicle in any public place."""},
{"n": 5, "t": "Responsibility of owners for contravention of sections 3 and 4", "c": """5. Responsibility of owners of motor vehicles for contravention of sections 3 and 4.—No owner or person in charge of a motor vehicle shall cause or permit any person who does not satisfy the provisions of section 3 or section 4 to drive the vehicle."""},
{"n": 9, "t": "Grant of driving licences", "c": """9. Grant of driving licences.—(1) Any person who is not disqualified under section 4 for driving a motor vehicle and who is not debarred from holding a driving licence may apply to the licensing authority having jurisdiction in the area in which he ordinarily resides or carries on business, for the issue to him of a driving licence. (2) Every application under sub-section (1) shall be in such form and shall be accompanied by such documents and shall contain such information as may be prescribed. (3) Subject to the provisions of sub-section (2), a person who holds a certificate of competence issued by a school or establishment whose certificates are recognised shall be deemed to have satisfied the prescribed requirements."""},
{"n": 10, "t": "Form and contents of licences", "c": """10. Form and contents of licences.—(1) Every driving licence shall be in such form and shall contain such information as may be prescribed by the Central Government. (2) A driving licence shall be issued to authorise the driving of motor vehicles of such classes or descriptions as may be specified therein. (3) A driving licence shall, unless it is suspended or is cancelled or has become invalid, be effective throughout India."""},
{"n": 14, "t": "Validity of driving licences", "c": """14. Validity of driving licences.—(1) A driving licence issued or renewed under this Act shall— (a) in the case of a licence to drive a transport vehicle, be effective for a period of three years; (b) in the case of any other licence— (i) if the person is under the age of thirty years, be effective for a period of twenty years or until the date on which such person attains the age of forty years, whichever is earlier; (ii) if such person is of the age of thirty years or more but less than fifty years, be effective for a period of ten years; (iii) if such person is of the age of fifty years or more, be effective for a period of five years."""},
{"n": 19, "t": "Power of licensing authority to disqualify or revoke driving licence", "c": """19. Power of licensing authority to disqualify from holding a driving licence or revoke such licence.—(1) If a licensing authority is satisfied, after giving the holder of a driving licence an opportunity of being heard, that he— (a) is a habitual criminal or a habitual drunkard; or (b) is a habitual addict to any narcotic drug or psychotropic substance; or (c) is using or has used a motor vehicle in the commission of a cognisable offence; or (d) has by his previous conduct as driver shown that his driving is likely to be attended with danger to the public; or (e) has obtained any driving licence by fraud or misrepresentation; or (f) has committed any specified offence, the authority may, for reasons to be recorded in writing, make an order— (i) disqualifying that person for a specified period for holding or obtaining a driving licence; or (ii) revoke the driving licence."""},
{"n": 39, "t": "Necessity for registration", "c": """39. Necessity for registration.—No person shall drive any motor vehicle and no owner of a motor vehicle shall cause or permit the vehicle to be driven in any public place or in any other place unless the vehicle is registered in accordance with this Chapter and the certificate of registration of the vehicle has not been suspended or cancelled and the vehicle carries a registration mark displayed in the prescribed manner."""},
{"n": 41, "t": "Registration of motor vehicles", "c": """41. Registration of motor vehicles.—(1) Subject to the provisions of section 42, every owner of a motor vehicle shall cause the vehicle to be registered by a registering authority in whose jurisdiction he has his residence or place of business at which the vehicle is normally kept. (2) The registering authority shall, on receipt of an application in the prescribed form accompanied by the prescribed documents, register the vehicle in the prescribed manner and issue a certificate of registration."""},
{"n": 49, "t": "Transfer of ownership", "c": """49. Transfer of ownership.—(1) Where the ownership of any motor vehicle registered under this Chapter is transferred,— (a) the transferor shall, within fourteen days of the transfer, report the transfer to the registering authority within whose jurisdiction the transfer is to take effect and shall simultaneously send a copy of the said report to the transferee; and (b) the transferee shall, within thirty days of the transfer, report the transfer to the registering authority within whose jurisdiction he has his residence or place of business. (2) On receipt of the report and documents, the registering authority shall update the certificate of registration to show the transferee as the registered owner."""},
{"n": 56, "t": "Certificate of fitness of transport vehicles", "c": """56. Certificate of fitness of transport vehicles.—(1) A transport vehicle shall not be deemed to be validly registered for the purposes of section 39 unless it carries a certificate of fitness issued by a designated officer that the vehicle complies with all requirements of this Act and the rules made thereunder. (2) The certificate of fitness shall be in such form and shall contain such particulars as may be prescribed. (3) A certificate of fitness shall be effective for two years unless it is suspended or cancelled earlier."""},
{"n": 66, "t": "Necessity for permits", "c": """66. Necessity for permits.—(1) No owner of a motor vehicle shall use or permit the use of the vehicle as a transport vehicle in any public place whether or not such vehicle is actually carrying any passengers or goods save in accordance with the conditions of a permit granted or countersigned by a Regional or State Transport Authority. (2) Sub-section (1) shall not apply to— (a) any vehicle owned by the Central Government or State Government not used as transport for hire or reward; (b) any vehicle used for relief work in a flood, accident or other emergency; (c) any vehicle used for training purposes by a driving school."""},
{"n": 112, "t": "Limits of speed", "c": """112. Limits of speed.—(1) No person shall drive a motor vehicle or cause or allow a motor vehicle to be driven in any public place at a speed exceeding the maximum speed or below the minimum speed fixed for the motor vehicle or the road or the area as the case may be under this Act or any other law for the time being in force or as displayed on the speed limit sign. (2) The maximum speed limits for motor vehicles shall be as specified in Schedule VII. (3) The State Government may, by notification, prescribe speed limits for any road or area lower than those specified in Schedule VII, having regard to the nature of the road and density of traffic."""},
{"n": 119, "t": "Duty to obey traffic signs", "c": """119. Duty to obey traffic signs.—(1) Every driver of a motor vehicle shall drive the vehicle in conformity with any indication given by the mandatory traffic sign and in conformity with the driving regulations made under section 118. (2) No owner or person in charge of a motor vehicle shall cause or permit the driver of the vehicle to contravene any mandatory traffic sign."""},
{"n": 122, "t": "Leaving vehicle in dangerous position", "c": """122. Leaving vehicle in dangerous position.—No person in charge of a motor vehicle shall cause or allow the vehicle or any trailer to remain stationary in any public place in such a position or in such a condition or in such circumstances as to cause or is likely to cause danger, obstruction or undue inconvenience to other users of the public place or to the passengers."""},
{"n": 129, "t": "Wearing of protective headgear", "c": """129. Wearing of protective headgear.—Every person driving or riding on a motor cycle of any class or description shall, while in a public place, wear protective headgear conforming to the standards of Bureau of Indian Standards: Provided that the provisions of this section shall not apply to a person who is a Sikh if he is wearing a turban."""},
{"n": 130, "t": "Duty to carry prescribed documents", "c": """130. Duty to carry prescribed documents.—(1) The driver of a motor vehicle in any public place shall, on being so required by a police officer in uniform or an officer of the Motor Vehicles Department in uniform, produce the prescribed documents for inspection. (2) The documents to be produced are: driving licence, certificate of registration, certificate of fitness if required, permit where necessary, and certificate of insurance."""},
{"n": 134, "t": "Duty of driver in case of accident and injury to a person", "c": """134. Duty of driver in case of accident and injury to a person.—When any person is injured or any property of a third party is damaged as a result of an accident in which a motor vehicle is involved, the driver of the vehicle shall— (a) take all reasonable steps to secure medical attention for the injured person, by conveying him to the nearest medical practitioner or hospital, and it shall be the duty of every registered medical practitioner or hospital to provide medical aid to every such injured person immediately without waiting for any formalities; (b) give on demand by a police officer any information required by him."""},
{"n": 145, "t": "Definitions – Insurance Chapter", "c": """145. Definitions.—In this Chapter,— (a) "authorised insurer" means an insurer for the time being carrying on general insurance business in India under the Insurance Act, 1938; (b) "certificate of insurance" means a certificate issued by an authorised insurer in pursuance of sub-section (3) of section 147; (c) "insurance policy" means a policy of insurance effected in accordance with the requirements of this Chapter; (d) "third party" includes the Government."""},
{"n": 146, "t": "Necessity for insurance against third party risk", "c": """146. Necessity for insurance against third party risk.—(1) No person shall use a motor vehicle in a public place unless there is in force in relation to the use of the vehicle a policy of insurance complying with the requirements of this Chapter: Provided that in the case of a vehicle carrying dangerous or hazardous goods, there shall also be a policy of insurance under the Public Liability Insurance Act, 1991. (2) The appropriate Government may, by order, exempt any vehicle owned by it from the requirements of this sub-section."""},
{"n": 147, "t": "Requirements of policies and limits of liability", "c": """147. Requirements of policies and limits of liability.—(1) In order to comply with the requirements of this Chapter, a policy of insurance must— (a) be issued by a person who is an authorised insurer; (b) insure the person specified in the policy— (i) against any liability which may be incurred by him in respect of the death of or bodily injury to any person or damage to any property of a third party caused by or arising out of the use of the vehicle in a public place; (ii) against the death of or bodily injury to any passenger of a public service vehicle caused by or arising out of the use of the vehicle in a public place."""},
{"n": 165, "t": "Claims Tribunals", "c": """165. Claims Tribunals.—(1) A State Government may, by notification in the Official Gazette, constitute one or more Motor Accidents Claims Tribunals for such area as may be specified in the notification for the purpose of adjudicating upon claims for compensation in respect of accidents involving the death of, or bodily injury to, persons arising out of the use of motor vehicles. (2) A Claims Tribunal shall consist of such number of members as the State Government may think fit to be appointed by the State Government by notification in the Official Gazette."""},
{"n": 177, "t": "General provision for punishment of offences", "c": """177. General provision for punishment of offences.—Whoever contravenes any provision of this Act or of any rule, regulation or notification made thereunder shall, if no penalty is provided for the offence, be punishable for the first offence with a fine which may extend to five hundred rupees, and for any subsequent offence with a fine which may extend to one thousand five hundred rupees."""},
{"n": 181, "t": "Driving without driving licence", "c": """181. Driving without driving licence.—Whoever drives a motor vehicle without a valid driving licence or causes or allows a motor vehicle to be driven without a valid driving licence shall be punishable with imprisonment for a term which may extend to three months, or with fine which may extend to five thousand rupees, or with both."""},
{"n": 183, "t": "Driving at excessive speed", "c": """183. Driving at excessive speed, etc.—(1) Whoever drives a motor vehicle in contravention of the speed limits referred to in section 112 shall be punishable— (a) for the first offence, with a fine of one thousand rupees for a motor cycle and two thousand rupees for any other motor vehicle; (b) for any subsequent offence committed within three years of the commission of the first offence, with a fine of two thousand rupees for a motor cycle and four thousand rupees for any other motor vehicle. (2) Whoever causes a motor vehicle to be driven in contravention of the speed limits shall be punishable with a fine of three hundred rupees, or if previously convicted, with a fine of five hundred rupees."""},
{"n": 184, "t": "Driving dangerously", "c": """184. Driving dangerously.—Whoever drives a motor vehicle at a speed or in a manner which is dangerous to the public having regard to all the circumstances of the case including the nature, condition and use of the place where the vehicle is driven and the amount of traffic which actually is at the time or which might reasonably be expected to be in the place shall be punishable for the first offence with imprisonment for a term which may extend to six months, or with fine which may extend to five thousand rupees, or with both, and for any subsequent offence committed within three years with imprisonment for a term which may extend to two years, or with fine which may extend to ten thousand rupees, or with both."""},
{"n": 185, "t": "Driving by a drunken person or under influence of drugs", "c": """185. Driving by a drunken person or by a person under the influence of drugs.—Whoever, while driving, or attempting to drive, a motor vehicle,— (a) has, in his blood, alcohol exceeding 30 mg. per 100 ml. of blood detected in a test by a breath analyser, or (b) is under the influence of a drug to such an extent as to be incapable of exercising proper control over the vehicle, shall be punishable for a first offence with imprisonment for a term of up to six months, or with fine up to ten thousand rupees, or with both; and for a subsequent offence, if committed within three years of the commission of the first offence, with imprisonment for a term of up to two years, or with fine up to fifteen thousand rupees, or with both."""},
{"n": 190, "t": "Using vehicle in unsafe condition", "c": """190. Using vehicle in unsafe condition.—(1) Any person who drives or causes or allows to be driven in any public place a motor vehicle which violates the standards prescribed in relation to road safety, control of noise and air pollution shall be punishable with a fine up to one thousand rupees, or with imprisonment up to three months, or with both. (2) If a person is convicted of an offence under this section, the court may order that the vehicle be not used until the vehicle complies with the prescribed standards."""},
{"n": 192, "t": "Using vehicle without registration", "c": """192. Using vehicle without registration.—(1) Whoever drives a motor vehicle or causes or allows a motor vehicle to be used in any public place without valid registration shall be punishable for a first offence with a fine not less than two thousand rupees but which may extend to five thousand rupees and for any subsequent offence with imprisonment for a term which may extend to one year or fine not less than five thousand rupees but which may extend to ten thousand rupees, or with both."""},
{"n": "192A", "t": "Using vehicle without permit", "c": """192A. Using vehicle without permit.—(1) Whoever uses a motor vehicle or causes or allows a motor vehicle to be used as a transport vehicle in any public place without a permit as required under this Act or in contravention of any condition of such permit shall be punishable for a first offence with a fine not less than two thousand rupees but which may extend to five thousand rupees, and for any subsequent offence with imprisonment up to one year or fine not less than five thousand rupees but which may extend to ten thousand rupees, or with both."""},
{"n": 194, "t": "Driving vehicle exceeding permissible weight", "c": """194. Driving vehicle exceeding permissible weight.—(1) Whoever drives a motor vehicle or causes or allows a motor vehicle to be driven when such motor vehicle— (a) exceeds the registered gross vehicle weight or the registered axle weight; or (b) is loaded in a manner likely to cause danger to persons in or on such motor vehicle or using the road, shall be punishable with fine of twenty thousand rupees and an additional amount of two thousand rupees per tonne of excess load, together with the liability to pay charges for off-loading of the excess load. (2) The fine collected under sub-section (1) shall be used for the maintenance of roads by the State Government."""},
{"n": 196, "t": "Driving uninsured vehicle", "c": """196. Driving uninsured vehicle.—Whoever drives a motor vehicle or causes or allows a motor vehicle to be driven without the vehicle being insured against third party risks as required by Chapter XI shall be punishable for a first offence with imprisonment for a term which may extend to three months, or with a fine which may extend to two thousand rupees, or with both, and for a subsequent offence with imprisonment for a term which may extend to three months, or with a fine which may extend to four thousand rupees, or with both."""},
{"n": 199, "t": "Offences by companies", "c": """199. Offences by companies.—(1) Where an offence under this Act has been committed by a company, every person who at the time the offence was committed was in charge of, and was responsible to, the company for the conduct of the business of the company, as well as the company, shall be deemed to be guilty of the offence and shall be liable to be proceeded against and punished accordingly. (2) Notwithstanding anything in sub-section (1), where any offence has been committed by a company and it is proved that the offence was committed with the consent or connivance of any director, manager, secretary or other officer of the company, such person shall also be deemed to be guilty of that offence."""},
{"n": 206, "t": "Power of police officer to impound document", "c": """206. Power of police officer to impound document.—(1) A police officer or an officer of the Motor Vehicles Department may, if he has reason to believe that any identification mark or document produced before him is a false document or the vehicle is being used in contravention of any provision of this Act, seize and impound the certificate of registration or any other relevant document relating to the vehicle."""},
{"n": 207, "t": "Power of police officer to detain vehicle", "c": """207. Power of police officer to detain vehicle.—(1) A police officer in uniform or an officer of the Motor Vehicles Department may detain a motor vehicle, if the vehicle is involved in an accident, or if the vehicle is being driven without a licence or registration or permit or certificate of fitness or certificate of insurance, or if the vehicle is overloaded or the vehicle is not in a roadworthy condition."""},
{"n": 215, "t": "Appeals", "c": """215. Appeals.—(1) Any person aggrieved by an order under this Act may, within thirty days of the date of receipt of the order, appeal to the authority prescribed in this behalf. The appellate authority shall give the person an opportunity of being heard before passing any order on the appeal."""},
{"n": 217, "t": "Repeal and savings", "c": """217. Repeal and savings.—(1) The Motor Vehicles Act, 1939 and the Motor Vehicles (Amendment) Act, 1969, shall stand repealed. (2) Notwithstanding such repeal, anything done or any action taken under the repealed enactments shall be deemed to have been done or taken under the corresponding provisions of this Act."""},
]

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    all_chunks = []

    # 1. MVA sections
    print(f"Processing MVA 1988 ({len(MVA_SECTIONS)} sections)...")
    for s in MVA_SECTIONS:
        n, title, content = s["n"], s["t"], s["c"]
        safe_n = str(n).replace("A", "a")
        meta = {
            "source":  "Motor Vehicles Act, 1988",
            "type":    "section",
            "chapter": get_mva_chapter(n),
            "act":     "Motor Vehicles Act, 1988",
            "year":    1988,
        }
        chunks = process_section(
            n, title, content,
            "Motor Vehicles Act, 1988",
            f"mva_s{safe_n}", meta
        )
        all_chunks.extend(chunks)
    mva_count = len(all_chunks)
    print(f"  → {mva_count} MVA chunks")

    # 2. CMVR rules from DB
    print(f"Loading CMVR from {DB_PATH}...")
    with open(DB_PATH, encoding="utf-8") as f:
        db = json.load(f)

    cmvr_start = len(all_chunks)
    for ruleset in db.get("rules", []):
        rules = ruleset.get("rules", [])
        print(f"Processing CMVR ({len(rules)} rules)...")
        for rule in rules:
            rn      = rule.get("rule_number", "?")
            rtitle  = rule.get("rule_title",  f"Rule {rn}")
            rcont   = rule.get("content",     "").strip()
            ch_num  = rule.get("chapter_number", -1)
            ch_name = CMVR_CHAPTERS.get(ch_num, rule.get("chapter_name", ""))
            app_sec = rule.get("appendix_section", "")
            if not rcont:
                continue

            chapter_str = (f"Appendices – {app_sec}" if ch_num == 0 and app_sec
                           else ch_name)
            safe = str(rn).replace("/", "_").replace(" ", "_")

            meta = {
                "source":          "Central Motor Vehicles Rules, 1989",
                "type":            "rule",
                "chapter":         chapter_str,
                "chapter_number":  ch_num,
                "act":             "Central Motor Vehicles Rules, 1989",
                "year":            1989,
                "source_pdf":      rule.get("source_file", ""),
                "keywords":        rule.get("keywords", []),
                "sub_rules_count": rule.get("sub_rules_count", 0),
            }
            if app_sec:
                meta["appendix_section"] = app_sec

            chunks = process_section(
                rn, rtitle, rcont,
                "Central Motor Vehicles Rules, 1989",
                f"cmvr_r{safe}", meta
            )
            all_chunks.extend(chunks)

    cmvr_count = len(all_chunks) - cmvr_start
    print(f"  → {cmvr_count} CMVR chunks")

    # Save
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(all_chunks, f, indent=2, ensure_ascii=False)

    size_kb   = os.path.getsize(OUT_PATH) / 1024
    tok_list  = [c["token_estimate"] for c in all_chunks]
    avg_tok   = sum(tok_list) // len(tok_list)
    under_600 = sum(1 for t in tok_list if t < 600)
    in_range  = sum(1 for t in tok_list if 600 <= t <= 900)
    over_900  = sum(1 for t in tok_list if t > 900)

    print("\n" + "=" * 60)
    print("RECURSIVE TEXT SPLITTER — DONE")
    print("=" * 60)
    print(f"  Output:            {OUT_PATH}")
    print(f"  File size:         {size_kb:.1f} KB")
    print(f"  Total chunks:      {len(all_chunks)}")
    print(f"  MVA chunks:        {mva_count}")
    print(f"  CMVR chunks:       {cmvr_count}")
    print(f"  Avg tokens/chunk:  {avg_tok}")
    print(f"  < 600 tokens:      {under_600}")
    print(f"  600–900 tokens:    {in_range}")
    print(f"  > 900 tokens:      {over_900}")
    print(f"\nSeparators used: {SEPARATORS}")
    print(f"Chunk size:   {CHUNK_SIZE} tokens ({CHUNK_CHARS} chars)")
    print(f"Overlap:      {CHUNK_OVERLAP} tokens ({OVERLAP_CHARS} chars)")
    print(f"\nSample chunks:")
    for c in all_chunks[:2]:
        print(f"  [{c['chunk_id']}] ~{c['token_estimate']} tokens | {c['section_title'][:45]}")

if __name__ == "__main__":
    main()
