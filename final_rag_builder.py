"""
final_rag_builder.py
====================
Builds complete motor_vehicles_rag_chunks.json from:
  - Motor Vehicles Act 1988 (all 19 key + structured sections)
  - Central Motor Vehicles Rules 1989 (from existing DB JSON)

Output: D:\moptor_vehical_dataset\motor_vehicles_rag_chunks.json
"""

import json, re, os

DB_PATH  = r"D:\moptor_vehical_dataset\motor_vehicles_db.json"
OUT_PATH = r"D:\moptor_vehical_dataset\motor_vehicles_rag_chunks.json"

CHARS_PER_TOKEN = 4
MAX_TOKENS = 900
OVERLAP = 0.15

# ── MVA Chapter mapping ───────────────────────────────────────────────────────
def mva_chapter(n):
    try:
        n = int(re.sub(r"[A-Za-z]", "", str(n)))
    except Exception:
        return "Unknown Chapter"
    for r, c in {
        range(1,3):   "Chapter I – Preliminary",
        range(3,27):  "Chapter II – Licensing of Drivers",
        range(27,39): "Chapter III – Licensing of Conductors",
        range(39,65): "Chapter IV – Registration of Motor Vehicles",
        range(65,97): "Chapter V – Control of Transport Vehicles",
        range(97,104):"Chapter VI – State Transport Undertakings",
        range(104,117):"Chapter VII – Construction & Equipment",
        range(117,142):"Chapter VIII – Control of Traffic",
        range(142,148):"Chapter IX – Vehicles Leaving India",
        range(148,151):"Chapter X – Liability Without Fault",
        range(151,165):"Chapter XI – Insurance Third Party",
        range(165,177):"Chapter XII – Claims Tribunals",
        range(177,211):"Chapter XIII – Offences & Penalties",
        range(211,218):"Chapter XIV – Miscellaneous",
    }.items():
        if n in r: return c
    return "Unknown Chapter"

# ── Full MVA 1988 sections ────────────────────────────────────────────────────
MVA_SECTIONS = [
{"n":1,"t":"Short title, extent and commencement","c":"""1. Short title, extent and commencement.—(1) This Act may be called the Motor Vehicles Act, 1988. (2) It extends to the whole of India. (3) It shall come into force on such date as the Central Government may, by notification in the Official Gazette, appoint."""},
{"n":2,"t":"Definitions","c":"""2. Definitions.—In this Act, unless the context otherwise requires,— (1) "adapted vehicle" means a motor vehicle specially constructed or adapted for use by invalids or persons suffering from physical defect or disability; (3) "axle weight" means the total weight transmitted by wheels of an axle to the road surface; (6) "certificate of fitness" means a certificate issued under section 56 that the vehicle is fit for use; (10) "conductor" means a person collecting fares from passengers in a stage carriage; (14) "driver" includes the steerer of a drawn vehicle; (20) "invalid carriage" means a motor vehicle specially constructed for use of a person suffering from physical defect; (21) "learner's licence" means a licence issued under Chapter II to drive as a learner; (28) "motor vehicle" or "vehicle" means any mechanically propelled vehicle adapted for use upon roads whether propelled from external or internal source, includes chassis without body and trailer; does not include vehicle on fixed rails, vehicle in enclosed premises, or vehicle with less than four wheels with engine not exceeding 25 cc; (29) "omnibus" means a motor vehicle constructed or adapted to carry more than six persons excluding the driver; (30) "owner" means a person in whose name a motor vehicle stands registered including a person making payments under a hire-purchase agreement; (34) "permit" means a permit issued under this Act; (40) "public place" means a road, street, way or other place to which the public have a right of access; (47) "stage carriage" means a motor vehicle constructed to carry more than six persons excluding driver and used for carrying passengers for hire or reward at separate fares."""},
{"n":3,"t":"Necessity for driving licence","c":"""3. Necessity for driving licence.—(1) No person shall drive a motor vehicle in any public place unless he holds an effective driving licence authorising him to drive the vehicle; and no person shall drive a transport vehicle unless his driving licence specifically entitles him so to do. (2) The conditions subject to which sub-section (1) shall not apply to a person receiving instruction in driving shall be prescribed by the Central Government."""},
{"n":4,"t":"Age limit in connection with driving","c":"""4. Age limit in connection with driving of motor vehicles.—(1) No person under the age of eighteen years shall drive a motor vehicle in any public place: Provided that a motor vehicle other than a transport vehicle may be driven by a person who has attained the age of sixteen years if such person is accompanied by a person holding an effective driving licence. (2) No person under the age of twenty years shall drive a transport vehicle in any public place."""},
{"n":5,"t":"Responsibility of owners of motor vehicles for contravention of sections 3 and 4","c":"""5. Responsibility of owners of motor vehicles for contravention of sections 3 and 4.—No owner or person in charge of a motor vehicle shall cause or permit any person who does not satisfy the provisions of section 3 or section 4 to drive the vehicle."""},
{"n":6,"t":"Restrictions on driving by transport companies","c":"""6. Restrictions on driving by transport companies.—Where a licence has been granted to drive transport vehicles under sub-section (1) of section 10, no person employed by a transport company to drive such vehicle shall drive such vehicle unless such person satisfies the requirements of section 3 and section 4."""},
{"n":9,"t":"Grant of driving licences","c":"""9. Grant of driving licences.—(1) Any person who is not disqualified under section 4 for driving a motor vehicle and who is not debarred from holding a driving licence may apply to the licensing authority having jurisdiction in the area in which he ordinarily resides or carries on business or in which the school or establishment referred to in sub-section (3) is situated, for the issue to him of a driving licence. (2) Every application under sub-section (1) shall be in such form and shall be accompanied by such documents and shall contain such information as may be prescribed. (3) Subject to the provisions of sub-section (2), a person who holds a certificate of competence issued by a school or establishment whose certificates are recognised shall be deemed to have satisfied the prescribed requirements."""},
{"n":10,"t":"Form and contents of licences","c":"""10. Form and contents of licences.—(1) Every driving licence shall be in such form and shall contain such information as may be prescribed by the Central Government. (2) A driving licence shall be issued to authorise the driving of motor vehicles of such classes or descriptions as may be specified therein. (3) A driving licence shall, unless it is suspended or is cancelled or has become invalid, be effective throughout India."""},
{"n":11,"t":"Additions to driving licence","c":"""11. Additions to driving licence.—Any person holding a driving licence may apply to the licensing authority in his jurisdiction to add to such licence an authorisation to drive any other class or description of motor vehicles and any such authorisation shall be granted in accordance with the provisions of this Chapter."""},
{"n":14,"t":"Validity of driver's licences","c":"""14. Validity of driving licences.—(1) A driving licence issued or renewed under this Act shall— (a) in the case of a licence to drive a transport vehicle, be effective for a period of three years; (b) in the case of any other licence— (i) if the person obtaining the licence, either originally or on renewal, is under the age of thirty years, be effective for a period of twenty years or until the date on which such person attains the age of forty years, whichever is earlier; (ii) if such person is of the age of thirty years or more but less than fifty years, be effective for a period of ten years; (iii) if such person is of the age of fifty years or more, be effective for a period of five years."""},
{"n":19,"t":"Power to disqualify from holding driving licence","c":"""19. Power of licensing authority to disqualify from holding a driving licence or revoke such licence.—(1) If a licensing authority is satisfied that the holder of a driving licence— (a) is a habitual criminal or habitual drunkard; (b) is a habitual addict to any narcotic drug; (c) is using a motor vehicle in the commission of a cognisable offence; (d) has shown dangerous driving conduct; (e) has obtained a driving licence by fraud or misrepresentation; (f) has committed any specified offence, the authority may disqualify that person for a specified period or revoke the driving licence."""},
{"n":39,"t":"Necessity for registration","c":"""39. Necessity for registration.—No person shall drive any motor vehicle and no owner shall cause or permit a vehicle to be driven in any public place or other place unless the vehicle is registered in accordance with this Chapter and the certificate of registration has not been suspended or cancelled and the vehicle carries a registration mark displayed in the prescribed manner."""},
{"n":41,"t":"Registration of motor vehicles","c":"""41. Registration of motor vehicles.—(1) Subject to the provisions of section 42, every owner of a motor vehicle shall cause the vehicle to be registered by a registering authority in whose jurisdiction he has his residence or place of business at which the vehicle is normally kept. (2) The owner shall present the vehicle for registration within seven days of the date of commencement of this Act or within such period as may be prescribed. (3) The registering authority shall, on receipt of an application, register the vehicle in the prescribed manner and issue a certificate of registration."""},
{"n":49,"t":"Transfer of ownership","c":"""49. Transfer of ownership.—(1) Where the ownership of any motor vehicle is transferred— (a) the transferor shall, within fourteen days of the transfer, report to the registering authority and simultaneously send a copy to the transferee; (b) the transferee shall, within thirty days of the transfer, report the transfer to the registering authority within whose jurisdiction he has his residence or place of business. (2) On receipt of the report and documents, the registering authority shall update the certificate of registration."""},
{"n":56,"t":"Certificate of fitness of transport vehicles","c":"""56. Certificate of fitness of transport vehicles.—(1) Subject to the provisions of section 59, a transport vehicle shall not be deemed to be validly registered for the purposes of section 39 unless it carries a certificate of fitness issued by a designated officer that the vehicle complies with all requirements of this Act and the rules made thereunder. (2) The certificate of fitness shall be in such form and shall contain such particulars as may be prescribed. (3) A certificate of fitness issued under this section shall be effective for two years unless it is suspended or cancelled earlier."""},
{"n":66,"t":"Necessity for permits","c":"""66. Necessity for permits.—(1) No owner of a motor vehicle shall use or permit the use of the vehicle as a transport vehicle in any public place whether or not carrying passengers or goods save in accordance with the conditions of a permit granted by a Regional or State Transport Authority. (2) Sub-section (1) shall not apply to— (a) any vehicle owned by the Central Government or State Government not used as a transport vehicle for hire or reward; (b) any vehicle used for relief work in a flood, accident or other emergency; (c) any vehicle used for training purposes by a driving school."""},
{"n":112,"t":"Limits of speed","c":"""112. Limits of speed.—(1) No person shall drive a motor vehicle or cause or allow a motor vehicle to be driven in any public place at a speed exceeding the maximum speed or below the minimum speed fixed for the motor vehicle or the road or the area as displayed on the speed limit sign. (2) The maximum speed limits for motor vehicles shall be as specified in Schedule VII. (3) The State Government may, by notification, prescribe speed limits for any road or area lower than those specified in Schedule VII, having regard to the nature of the road and density of traffic."""},
{"n":113,"t":"Limits of weight and laden weight","c":"""113. Limits of weight and laden weight.—(1) No person shall drive or cause or allow to be driven in any public place any motor vehicle or trailer the weight of which, including its load, exceeds the maximum permissible laden weight fixed in respect of that vehicle, and no person shall cause or allow the weight transmitted to any axle to exceed the maximum weight as specified."""},
{"n":119,"t":"Duty to obey traffic signs","c":"""119. Duty to obey traffic signs.—(1) Every driver of a motor vehicle shall drive the vehicle in conformity with any indication given by the mandatory traffic sign and in conformity with the driving regulations made under section 118. (2) No owner or person in charge of a motor vehicle shall cause or permit the driver of the vehicle to contravene any mandatory traffic sign."""},
{"n":122,"t":"Leaving vehicle in dangerous position","c":"""122. Leaving vehicle in dangerous position.—No person in charge of a motor vehicle shall cause or allow the vehicle or any trailer to remain stationary in any public place in such a position or in such a condition or in such circumstances as to cause or is likely to cause danger, obstruction or undue inconvenience to other users of the public place or to the passengers."""},
{"n":123,"t":"Riding on running board","c":"""123. Riding on running board, etc.—No person shall travel in or on a motor vehicle in such a manner as to be a source of danger to himself or to other persons in the vehicle or in a public place and no owner or driver of a motor vehicle shall cause or permit any person so to travel."""},
{"n":128,"t":"Safety measures for drivers and pillion riders","c":"""128. Safety measures for drivers and pillion riders.—(1) No driver of a two-wheeled motor vehicle shall carry more than one person in addition to himself on the vehicle. (2) No driver shall carry on a two-wheeled motor vehicle a child who is less than four years of age."""},
{"n":129,"t":"Wearing of protective headgear","c":"""129. Wearing of protective headgear.—Every person driving or riding on a motor cycle of any class or description shall, while in a public place, wear protective headgear conforming to the standards of Bureau of Indian Standards: Provided that the provisions of this section shall not apply to a person who is a Sikh if he is wearing a turban."""},
{"n":130,"t":"Duty to carry prescribed documents","c":"""130. Duty to carry prescribed documents.—(1) The driver of a motor vehicle in any public place shall, on being so required by a police officer in uniform or an officer of the Motor Vehicles Department in uniform, produce the prescribed documents for inspection. (2) The prescribed documents are driving licence, certificate of registration, certificate of fitness if required, permit where necessary, and certificate of insurance."""},
{"n":134,"t":"Duty of driver in case of accident and injury to a person","c":"""134. Duty of driver in case of accident and injury to a person.—When any person is injured or any property of a third party is damaged as a result of an accident in which a motor vehicle is involved, the driver of the vehicle shall— (a) take all reasonable steps to secure medical attention for the injured person, by conveying him to the nearest medical practitioner or hospital, and it shall be the duty of every registered medical practitioner or hospital to provide medical aid to every such injured person immediately without waiting for any formalities; (b) give on demand by a police officer any information required by him."""},
{"n":145,"t":"Definitions – Insurance","c":"""145. Definitions.—In this Chapter,— (a) "authorised insurer" means an insurer carrying on general insurance business in India under the Insurance Act, 1938; (b) "certificate of insurance" means a certificate issued by an authorised insurer in pursuance of sub-section (3) of section 147; (c) "insurance policy" means a policy of insurance effected in accordance with the requirements of this Chapter; (d) "third party" includes the Government."""},
{"n":146,"t":"Necessity for insurance against third party risk","c":"""146. Necessity for insurance against third party risk.—(1) No person shall use a motor vehicle in a public place unless there is in force a policy of insurance complying with the requirements of this Chapter: Provided that in the case of a vehicle carrying dangerous or hazardous goods, there shall also be a policy of insurance under the Public Liability Insurance Act, 1991. (2) The appropriate Government may, by order, exempt any vehicle owned by it from the requirements of this sub-section."""},
{"n":147,"t":"Requirements of policies and limits of liability","c":"""147. Requirements of policies and limits of liability.—(1) In order to comply with the requirements of this Chapter, a policy of insurance must be a policy which— (a) is issued by a person who is an authorised insurer; (b) insures the person specified in the policy to the extent specified in sub-section (2)— (i) against any liability which may be incurred by him in respect of the death of or bodily injury to any person or damage to any property of a third party caused by or arising out of the use of the vehicle in a public place; (ii) against the death of or bodily injury to any passenger of a public service vehicle caused by or arising out of the use of the vehicle in a public place."""},
{"n":158,"t":"Production of certain certificates, licence and permit to police officer","c":"""158. Production of certain certificates, licence and permit to police officer.—(1) Any person driving a motor vehicle in any public place shall, on being so required by a police officer in uniform, produce the certificate of insurance, the certificate of registration, the driving licence, and in the case of a transport vehicle the certificate of fitness and permit."""},
{"n":165,"t":"Claims Tribunals","c":"""165. Claims Tribunals.—(1) A State Government may, by notification in the Official Gazette, constitute one or more Motor Accidents Claims Tribunals for such area as may be specified in the notification for the purpose of adjudicating upon claims for compensation in respect of accidents involving the death of, or bodily injury to, persons arising out of the use of motor vehicles. (2) A Claims Tribunal shall consist of such number of members as the State Government may think fit and shall be appointed by the State Government by notification in the Official Gazette."""},
{"n":177,"t":"General provision for punishment of offences","c":"""177. General provision for punishment of offences.—Whoever contravenes any provision of this Act or of any rule, regulation or notification made thereunder shall, if no penalty is provided for the offence, be punishable for the first offence with a fine which may extend to five hundred rupees, and for any subsequent offence with a fine which may extend to one thousand five hundred rupees."""},
{"n":178,"t":"Penalty for travelling without pass or ticket","c":"""178. Penalty for travelling without pass or ticket.—(1) If any person travels or attempts to travel in a stage carriage without pass or ticket or having a ticket for a place other than the place to which he intends to travel, or fails to show his pass or ticket, he shall be punishable with fine not exceeding two hundred rupees."""},
{"n":179,"t":"Penalty for obstructing driver of motor vehicle","c":"""179. Penalty for obstructing driver of motor vehicle.—Whoever wilfully prevents, obstructs or interferes with the free movement of traffic, or wilfully obstructs or prevents the driver of a motor vehicle from driving the vehicle, or seizes or interferes with the steering mechanism or any other part of the vehicle while it is in motion shall be punishable with fine which may extend to one thousand rupees."""},
{"n":181,"t":"Driving without driving licence","c":"""181. Driving without driving licence.—Whoever drives a motor vehicle without a valid driving licence or causes or allows a motor vehicle to be driven without a valid driving licence shall be punishable with imprisonment for a term which may extend to three months, or with fine which may extend to five thousand rupees, or with both."""},
{"n":182,"t":"Offences relating to licences","c":"""182. Offences relating to licences.—(1) Whoever drives a motor vehicle in contravention of any condition of the driving licence shall be punishable for the first offence with a fine which may extend to five hundred rupees and for any subsequent offence with imprisonment for a term which may extend to three months, or with fine which may extend to one thousand five hundred rupees, or with both. (2) Whoever drives a motor vehicle in contravention of section 6 shall be punishable with a fine which may extend to five hundred rupees."""},
{"n":183,"t":"Driving at excessive speed","c":"""183. Driving at excessive speed, etc.—(1) Whoever drives a motor vehicle in contravention of the speed limits referred to in section 112 shall be punishable— (a) for the first offence, with a fine of one thousand rupees for a motor cycle and two thousand rupees for any other motor vehicle; (b) for any subsequent offence committed within three years of the first offence, with a fine of two thousand rupees for a motor cycle and four thousand rupees for any other motor vehicle. (2) Whoever causes a motor vehicle to be driven in contravention of speed limits shall be punishable with a fine of three hundred rupees, or for subsequent offence five hundred rupees."""},
{"n":184,"t":"Driving dangerously","c":"""184. Driving dangerously.—Whoever drives a motor vehicle at a speed or in a manner which is dangerous to the public having regard to all the circumstances including the nature, condition and use of the place where the vehicle is driven and the amount of traffic shall be punishable for the first offence with imprisonment for a term which may extend to six months, or with fine which may extend to five thousand rupees, or with both, and for any subsequent offence within three years with imprisonment up to two years, or fine up to ten thousand rupees, or with both."""},
{"n":185,"t":"Driving by a drunken person or under influence of drugs","c":"""185. Driving by a drunken person or by a person under the influence of drugs.—Whoever while driving or attempting to drive a motor vehicle— (a) has, in his blood, alcohol exceeding 30 mg. per 100 ml. of blood detected in a test by a breath analyser, or (b) is under the influence of a drug incapable of exercising proper control over the vehicle, shall be punishable for a first offence with imprisonment up to six months, or fine up to ten thousand rupees, or with both; and for subsequent offence within three years with imprisonment up to two years, or fine up to fifteen thousand rupees, or with both."""},
{"n":186,"t":"Driving when mentally or physically unfit","c":"""186. Driving when mentally or physically unfit to drive.—Whoever drives a motor vehicle in any public place when he is to his knowledge suffering from any disease or disability calculated to cause his driving of the vehicle to be a source of danger to the public shall be punishable with fine which may extend to two hundred rupees for the first offence and five hundred rupees for any subsequent offence."""},
{"n":187,"t":"Punishment for offences relating to accident","c":"""187. Punishment for offences relating to accident.—Whoever fails to comply with the provisions of clause (a) of sub-section (1) or of sub-section (2) of section 132 or of section 133 or section 134 shall be punishable with imprisonment for a term which may extend to three months, or with fine which may extend to five hundred rupees, or with both, or, if having been previously convicted of an offence under this section is again convicted of an offence under this section, with imprisonment up to six months, or fine up to one thousand rupees, or with both."""},
{"n":188,"t":"Punishment for abetment of certain offences","c":"""188. Punishment for abetment of certain offences.—Whoever abets the commission of an offence under section 184 or section 185 shall be punishable with the punishment provided for the offence."""},
{"n":189,"t":"Racing and trials of speed","c":"""189. Racing and trials of speed.—Whoever without the written consent of the State Government permits or takes part in a race or trial of speed of any kind between motor vehicles in any public place shall be punishable with imprisonment for a term which may extend to one month, or with fine which may extend to five hundred rupees, or with both."""},
{"n":190,"t":"Using vehicle in unsafe condition","c":"""190. Using vehicle in unsafe condition.—(1) Any person who drives or causes or allows to be driven in any public place a motor vehicle which violates the standards prescribed in relation to road safety, control of noise and air pollution shall be punishable with a fine up to one thousand rupees, or with imprisonment up to three months, or with both. (2) If a person is convicted of an offence under this section, the court may, in addition to imposing any punishment, order that the vehicle be not used until the vehicle complies with the prescribed standards."""},
{"n":192,"t":"Using vehicle without registration","c":"""192. Using vehicle without registration.—(1) Whoever drives a motor vehicle or causes or allows a motor vehicle to be used in any public place without valid registration shall be punishable for a first offence with a fine not less than two thousand rupees but which may extend to five thousand rupees and for any subsequent offence with imprisonment for a term which may extend to one year or fine not less than five thousand rupees but which may extend to ten thousand rupees, or with both."""},
{"n":"192A","t":"Using vehicle without permit","c":"""192A. Using vehicle without permit.—(1) Whoever uses a motor vehicle or causes or allows a motor vehicle to be used as a transport vehicle in any public place without a permit as may be required under this Act or in contravention of any condition of such permit shall be punishable for a first offence with a fine not less than two thousand rupees but which may extend to five thousand rupees, and for any subsequent offence with imprisonment up to one year or fine not less than five thousand rupees but which may extend to ten thousand rupees, or with both."""},
{"n":194,"t":"Driving vehicle exceeding permissible weight","c":"""194. Driving vehicle exceeding permissible weight.—(1) Whoever drives a motor vehicle or causes or allows a motor vehicle to be driven when such motor vehicle— (a) exceeds the registered gross vehicle weight or the registered axle weight; or (b) is loaded in a manner likely to cause danger to persons in or on such motor vehicle or using the road, shall be punishable with fine of twenty thousand rupees and an additional amount of two thousand rupees per tonne of excess load, together with liability to pay charges for off-loading of the excess load. (2) The fine collected under sub-section (1) shall be used for the maintenance of roads by the State Government."""},
{"n":196,"t":"Driving uninsured vehicle","c":"""196. Driving uninsured vehicle.—Whoever drives a motor vehicle or causes or allows a motor vehicle to be driven without insurance against third party risks as required by Chapter XI shall be punishable for a first offence with imprisonment up to three months, or fine up to two thousand rupees, or with both, and for any subsequent offence with imprisonment up to three months, or fine up to four thousand rupees, or with both."""},
{"n":199,"t":"Offences by companies","c":"""199. Offences by companies.—(1) Where an offence under this Act has been committed by a company, every person who at the time the offence was committed was in charge of, and was responsible to, the company for the conduct of the business shall be deemed to be guilty of the offence and shall be liable to be proceeded against and punished accordingly. (2) Notwithstanding anything in sub-section (1), where any offence has been committed by a company and it is proved that the offence was committed with the consent or connivance of any director, manager, secretary or other officer of the company, such person shall also be deemed to be guilty of that offence."""},
{"n":206,"t":"Power of police officer to impound document","c":"""206. Power of police officer to impound document.—(1) A police officer or an officer of the Motor Vehicles Department authorised in this behalf by the State Government may, if he has reason to believe that any identification mark or document produced before him is a false document or the vehicle is being used in contravention of any provision of this Act, seize and impound the certificate of registration or any other relevant document relating to the vehicle."""},
{"n":207,"t":"Power of police officer to detain vehicle","c":"""207. Power of police officer to detain vehicle.—(1) A police officer in uniform or an officer of the Motor Vehicles Department may detain a motor vehicle, if the vehicle is involved in an accident, or if the vehicle is being driven without a licence or registration or permit or certificate of fitness or certificate of insurance, or if the vehicle is overloaded or the vehicle is not in a roadworthy condition."""},
{"n":210,"t":"Courts to send intimation about conviction","c":"""210. Courts to send intimation about conviction.—(1) Where a person is convicted of an offence under this Act, the court shall send to the licensing authority by which the licence was issued a copy of the order of conviction within a period of fourteen days of such conviction."""},
{"n":211,"t":"Power of State Government to make rules","c":"""211. Power of State Government to make rules.—The State Government may make rules for the purpose of carrying into effect the provisions of this Act in respect of— (a) the condition of roads; (b) the testing of vehicles; (c) road safety measures; (d) all other matters not specifically provided for in this Act."""},
{"n":213,"t":"National Road Safety and Traffic Management Board","c":"""213. National Road Safety and Traffic Management Board.—(1) The Central Government shall constitute a Board to be known as the National Road Safety and Traffic Management Board to exercise the powers and perform the functions conferred on it under this Act. (2) The Board shall consist of a Chairperson and such number of other members as may be prescribed."""},
{"n":215,"t":"Appeals","c":"""215. Appeals.—(1) Any person aggrieved by an order under this Act may, within thirty days of the date of receipt of the order, appeal to the authority prescribed in this behalf. The appellate authority shall give the person an opportunity of being heard before passing any order."""},
{"n":217,"t":"Repeal and savings","c":"""217. Repeal and savings.—(1) The Motor Vehicles Act, 1939 and the Motor Vehicles (Amendment) Act, 1969, shall stand repealed. (2) Notwithstanding such repeal, anything done or any action taken under the repealed enactments shall be deemed to have been done or taken under the corresponding provisions of this Act."""},
]

# ── Helpers ───────────────────────────────────────────────────────────────────
def est_tokens(t): return len(t) // CHARS_PER_TOKEN

def clean(text):
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    return text.strip()

def split_subsections(text):
    pat = re.compile(
        r"(?:\n|^)(\s*(?:\(\d+\)|\([a-z]\)|\([ivx]+\)"
        r"|Provided that|Explanation|Exception))",
        re.MULTILINE
    )
    splits = list(pat.finditer(text))
    if not splits:
        return [text]
    parts, prev = [], 0
    for m in splits:
        chunk = text[prev:m.start()].strip()
        if chunk: parts.append(chunk)
        prev = m.start()
    parts.append(text[prev:].strip())
    return [p for p in parts if p]

def make_chunks(content, sec_num, title, act, sec_key, meta):
    content = clean(content)
    if est_tokens(content) <= MAX_TOKENS:
        return [{"act_name":act,"section_number":str(sec_num),"section_title":title,
                 "chunk_id":f"{sec_key}_chunk_1","chunk_text":content,
                 "metadata":dict(meta,chunk_index=1,total_chunks=1)}]

    parts = split_subsections(content)
    windows, cur, cur_len = [], [], 0
    for part in parts:
        plen = est_tokens(part)
        if cur_len + plen > MAX_TOKENS and cur:
            windows.append("\n".join(cur))
            ov = "\n".join(cur)
            ov = ov[-int(len(ov)*OVERLAP):]
            cur, cur_len = [ov, part], est_tokens(ov) + plen
        else:
            cur.append(part); cur_len += plen
    if cur: windows.append("\n".join(cur))

    total = len(windows)
    return [{"act_name":act,"section_number":str(sec_num),"section_title":title,
             "chunk_id":f"{sec_key}_chunk_{i+1}","chunk_text":clean(w),
             "metadata":dict(meta,chunk_index=i+1,total_chunks=total)}
            for i, w in enumerate(windows)]

# ── Build chunks ──────────────────────────────────────────────────────────────
def main():
    all_chunks = []

    # 1. MVA 1988 sections
    print(f"Processing MVA 1988: {len(MVA_SECTIONS)} sections")
    for s in MVA_SECTIONS:
        n, title, content = s["n"], s["t"], s["c"]
        meta = {
            "source": "Motor Vehicles Act, 1988",
            "type": "section",
            "chapter": mva_chapter(n),
            "act": "Motor Vehicles Act, 1988",
            "year": 1988,
        }
        chunks = make_chunks(content, n, title, "Motor Vehicles Act, 1988",
                             f"mva_s{n}", meta)
        all_chunks.extend(chunks)
    mva_count = len(all_chunks)
    print(f"  → {mva_count} MVA chunks")

    # 2. Load CMVR from existing DB
    print(f"Loading CMVR from {DB_PATH}")
    with open(DB_PATH, encoding="utf-8") as f:
        db = json.load(f)

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

    cmvr_start = len(all_chunks)
    for ruleset in db.get("rules", []):
        rules = ruleset.get("rules", [])
        print(f"Processing CMVR: {len(rules)} rules")
        for rule in rules:
            rn     = rule.get("rule_number", "?")
            rtitle = rule.get("rule_title", f"Rule {rn}")
            rcont  = rule.get("content", "").strip()
            ch_num = rule.get("chapter_number", -1)
            ch_name= CMVR_CHAPTERS.get(ch_num, rule.get("chapter_name",""))
            app_sec= rule.get("appendix_section","")
            if not rcont: continue

            chapter_str = (f"Appendices – {app_sec}" if ch_num == 0 and app_sec
                           else ch_name)
            safe = str(rn).replace("/","_").replace(" ","_")
            meta = {
                "source": "Central Motor Vehicles Rules, 1989",
                "type": "rule",
                "chapter": chapter_str,
                "chapter_number": ch_num,
                "act": "Central Motor Vehicles Rules, 1989",
                "year": 1989,
                "source_pdf": rule.get("source_file",""),
                "keywords": rule.get("keywords",[]),
                "sub_rules_count": rule.get("sub_rules_count",0),
            }
            if app_sec: meta["appendix_section"] = app_sec

            chunks = make_chunks(rcont, rn, rtitle,
                                 "Central Motor Vehicles Rules, 1989",
                                 f"cmvr_r{safe}", meta)
            all_chunks.extend(chunks)

    cmvr_count = len(all_chunks) - cmvr_start
    print(f"  → {cmvr_count} CMVR chunks")

    # Save
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(all_chunks, f, indent=2, ensure_ascii=False)

    size_kb = os.path.getsize(OUT_PATH) / 1024
    tok = [est_tokens(c["chunk_text"]) for c in all_chunks]
    print(f"\n{'='*55}")
    print("COMPLETE RAG DATASET BUILT")
    print(f"{'='*55}")
    print(f"  File:          {OUT_PATH}")
    print(f"  Size:          {size_kb:.1f} KB")
    print(f"  Total chunks:  {len(all_chunks)}")
    print(f"  MVA chunks:    {mva_count}")
    print(f"  CMVR chunks:   {cmvr_count}")
    print(f"  Avg tokens:    {sum(tok)//len(tok)}")
    print(f"  < 600 tokens:  {sum(1 for t in tok if t<600)}")
    print(f"  600-900 tokens:{sum(1 for t in tok if 600<=t<=900)}")
    print(f"  > 900 tokens:  {sum(1 for t in tok if t>900)}")

if __name__ == "__main__":
    main()
