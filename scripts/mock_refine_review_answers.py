"""리뷰 설문 답변과 본문을 실제 입력 폼(기호성만 필수, 나머지 선택) 기준으로 현실화한다.

- PALATABILITY(기호성), FEEDING_CONVENIENCE(급여 편의성): 필수 -> 항상 응답.
  DIGESTION/SKIN_COAT/WEIGHT_VITALITY/ALLERGY: 선택 -> 확률적으로 미응답(review_answer = NULL, 행은 유지). 건강 고민 태그와 관련된 문항·사용기간이 긴 리뷰는 응답률 상향.
- 4~5점 리뷰(235건): 응답한 문항의 답변을 현실적인 비율로 다시 뽑고, 본문을 응답 내용에 맞춰 재작성
  (본문에 언급되는 항목은 반드시 응답이 있는 항목).
- 1~3점 리뷰(52건): 본문과 주 불만 항목 답변은 유지, 그 외 선택 문항만 미응답 처리 가능.
- 답변 매핑: NEGATIVE=나빠졌어요/안 먹어요/불편해요, NEUTRAL=그대로예요/보통이에요, POSITIVE=좋아졌어요/잘 먹어요/편해요
  ALLERGY는 폼 선택지가 "없었어요/있었어요" 2개뿐이라 POSITIVE=없었어요, NEGATIVE=있었어요 (NEUTRAL 미사용)
- usage_period: 폼의 자유 입력(예: 12일)을 반영해 3~120일로 다시 뽑고 본문의 N일 언급과 일치시킴
- 본문은 쿠팡 후기처럼 단문/중문/장문을 섞어 작성 (review.text varchar(255) 이내)
시드 고정(2028). 이미 적용돼 있으면 종료.
"""
import os
import re
import numpy as np
import openpyxl

HERE = os.path.dirname(os.path.abspath(__file__))
PATH = os.path.join(HERE, "..", "data", "mock", "상품 목데이터",
                    "golajulgaenyang_full_schema_mockdata_product_thumbnails_linked.xlsx")
RNG = np.random.default_rng(2028)
MARK = "리뷰 설문 응답"

# 1~3점 본문에서 주 불만 항목을 찾기 위해 별점 조정 스크립트의 문구 풀을 재사용
_src = open(os.path.join(HERE, "mock_rebalance_review_ratings.py"), encoding="utf-8").read()
_ns = {"__file__": os.path.join(HERE, "mock_rebalance_review_ratings.py")}
exec(_src.split("wb = openpyxl.load_workbook(PATH)")[0], _ns)
LOW_POOLS = {"PALATABILITY": [p for v in list(_ns["PAL"].values()) + list(_ns["PAL_MILD"].values()) for p in v]}
for k in _ns["ISSUE_TXT"]:
    LOW_POOLS[k] = _ns["ISSUE_TXT"][k] + _ns["ISSUE_MILD"][k]


def main_issue(text):
    for k, pool in LOW_POOLS.items():
        if any(p in text for p in pool):
            return k
    return None


OPTIONAL = ["DIGESTION", "SKIN_COAT", "WEIGHT_VITALITY", "ALLERGY"]
REQUIRED = ["PALATABILITY", "FEEDING_CONVENIENCE"]
FILL = {"DIGESTION": .65, "SKIN_COAT": .50, "WEIGHT_VITALITY": .45, "ALLERGY": .35}
CONCERN = {"DIGESTION": {"DIGESTION"}, "SKIN_COAT": {"SKIN_COAT", "HAIRBALL", "EYE"},
           "WEIGHT_VITALITY": {"WEIGHT", "JOINT"}, "ALLERGY": {"SKIN_COAT"}, "FEEDING_CONVENIENCE": set()}
SLOW = {"SKIN_COAT", "WEIGHT_VITALITY"}  # 효과 확인에 시간이 걸리는 문항
# 4~5점 리뷰의 응답 분포 (POSITIVE, NEUTRAL)
P_POS = {"DIGESTION": .55, "SKIN_COAT": .45, "WEIGHT_VITALITY": .40, "ALLERGY": 1.0, "FEEDING_CONVENIENCE": .60}

MENTION = {
    ("DIGESTION", "POSITIVE"): ["급여 후 변 상태가 좋아졌어요", "배변이 한결 좋아졌어요", "변이 단단해지고 냄새도 덜해요"],
    ("DIGESTION", "NEUTRAL"): ["배변 상태는 그대로예요", "배변은 크게 달라지지 않았어요", "변 상태는 평소와 비슷해요"],
    ("SKIN_COAT", "POSITIVE"): ["털에 윤기가 생겼어요", "긁는 횟수가 줄고 모질이 좋아졌어요", "피부 상태가 한결 나아졌어요"],
    ("SKIN_COAT", "NEUTRAL"): ["피부와 털 상태는 그대로예요", "모질은 아직 큰 변화는 없어요", "털 상태는 비슷해요"],
    ("WEIGHT_VITALITY", "POSITIVE"): ["활력이 좋아졌어요", "산책할 때 기운이 더 넘쳐요", "체중이 안정되고 활동량이 늘었어요"],
    ("WEIGHT_VITALITY", "NEUTRAL"): ["체중과 활력은 그대로예요", "체중 변화는 아직 없어요", "활동량은 평소와 비슷해요"],
    ("ALLERGY", "POSITIVE"): ["알러지 반응은 없었어요", "먹고 나서 이상 반응은 없었어요", "알러지 증상 없이 잘 먹고 있어요"],
    ("FEEDING_CONVENIENCE", "POSITIVE"): ["급여하기 편해요", "소분이 쉬워서 관리하기 좋아요", "한 번에 먹이기 편한 형태예요"],
    ("FEEDING_CONVENIENCE", "NEUTRAL"): ["급여 방법은 무난해요", "급여하기에 보통 정도예요"],
}
SP = {"DOG": "강아지", "CAT": "고양이"}
CTX = {
    "FOOD": ["{sp} 사료 바꿔보려고 후기 보고 주문했어요.", "원래 먹던 사료를 질려해서 새로 사봤어요.", "{sp} 먹일 사료 찾다가 구매했어요."],
    "TREAT": ["{sp} 간식으로 구매했어요.", "훈련할 때 쓰려고 주문했어요.", "후기가 좋아서 간식으로 사봤어요."],
    "SUPPLEMENT": ["{sp} 영양제 찾다가 구매했어요.", "먹이던 영양제를 바꿔보려고 주문했어요.", "후기 보고 {sp} 영양제로 사봤어요."],
}
USAGE = ["{u}일째 먹이고 있어요.", "{u}일 정도 먹여봤어요.", "{u}일째 급여 중입니다.", "{u}일 먹여본 후기예요."]
PAL_POS = {
    "FOOD": ["{s} 그릇 앞에서 기다릴 정도로 잘 먹어요.", "바꾼 첫날부터 싹 비웠어요.", "{s} 냄새 맡자마자 달려와서 먹어요."],
    "TREAT": ["{s} 봉지 소리만 나도 달려와요.", "주면 정신없이 먹어요.", "{s} 너무 좋아해서 금방 없어져요."],
    "SUPPLEMENT": ["{s} 그냥 줘도 잘 먹어서 편해요.", "간식인 줄 아는지 잘 받아먹어요.", "거부감 없이 잘 먹어줘서 다행이에요."],
}
PAL_NEU = ["{s} 그냥 무난하게 먹는 편이에요.", "엄청 좋아하진 않아도 남기지는 않아요.", "{t} 먹긴 먹는데 폭풍흡입은 아니에요."]
EXTRA = ["배송도 빨라서 좋았어요.", "포장 꼼꼼하게 와서 만족해요.", "가격 대비 양이 넉넉해요.", "유통기한도 넉넉하게 왔어요."]
EXTRA_LOW = {1: ["처음 사서 기대가 컸는데 많이 아쉬워요.", "후기가 좋길래 샀는데 저희 아이한테는 안 맞았어요.", "남은 건 다른 용도로 보관 중이에요."],
             2: ["기대했던 것보다는 아쉬웠어요.", "후기랑 달라서 조금 당황했어요."],
             3: ["가격 생각하면 그냥 그래요.", "배송은 빨랐고 포장도 괜찮았어요."]}
CLOSE5 = ["강추합니다!", "다음에도 재구매할게요.", "믿고 먹이는 제품이에요, 재구매 의사 100%예요.", "주변 반려인들에게도 추천하고 싶어요."]
CLOSE4 = ["만족스러워요, 재구매 예정이에요.", "전체적으로 괜찮아요. 한 번 더 사볼 생각이에요."]
CLOSE_NEU = ["좀 더 지켜보고 재구매 결정할게요.", "나쁘진 않은데 조금 더 먹여봐야 알 것 같아요."]
# 문구 길이 유형: (비중, 맥락 문장, 사용기간 문장, 문항 언급, 부가 문장 확률)
STORY = ["처음엔 반신반의했는데 써보니 만족스러워요.", "다른 제품 먹이다 갈아탔는데 잘한 선택 같아요.", "주변에서 추천받아 사봤는데 후기대로 괜찮네요.",
         "고민하다가 샀는데 진작 살걸 그랬어요."]
STORY_NEU = ["후기가 갈려서 고민하다 샀어요.", "다른 제품이랑 비교하다 샀는데 아직은 판단이 어려워요."]
STORY_LOW = {1: ["후기가 좋길래 반신반의하며 샀는데 역시 아쉬웠어요.", "다른 반려인분들은 잘 맞았다는데 저희는 아니었어요."],
             2: ["고민 끝에 샀는데 기대에는 못 미쳤어요.", "다른 후기랑은 조금 달랐어요."],
             3: ["후기가 갈려서 고민하다 샀어요.", "다른 제품이랑 비교하다 샀는데 딱 중간 정도예요."]}
TIP = ["처음엔 조금씩 섞어서 급여하는 걸 추천해요.", "개봉 후에는 밀봉해서 보관하고 있어요.", "급여량은 포장지 가이드대로 맞췄어요.",
       "다른 {sp} 키우시는 분들도 한번 써보셨으면 좋겠어요."]
# 문구 길이 유형: (비중, 맥락 문장, 사용기간 문장, 문항 언급, 부가 문장 개수 확률, 스토리/팁 문장 확률)
MODES = [(.30, 0, .3, .25, .1, 0), (.40, .6, .7, .55, .5, .35), (.30, 1, 1, .95, 1.0, .9)]
ROUND_DAYS = [7, 10, 14, 15, 20, 21, 30, 45, 60, 90]


def josa(name, with_final, without_final):
    """이름 끝 글자 받침 유무에 따라 조사를 붙인다."""
    return name + (with_final if (ord(name[-1]) - 0xAC00) % 28 else without_final)


def pick(lst):
    return lst[RNG.integers(len(lst))]


wb = openpyxl.load_workbook(PATH)
rs = wb["README"]
if any(str(c.value).startswith(MARK) for c in rs["A"]):
    print("이미 적용돼 있습니다."); raise SystemExit

def tbl(ws):
    h = {c.value: c.column - 1 for c in ws[1]}
    return h, [r for r in ws.iter_rows(min_row=2) if r[0].value is not None]

rh, rrows = tbl(wb["review"])
qh, qrows = tbl(wb["review_question"])
ch, crows = tbl(wb["review_health_concern"])
ph, prows = tbl(wb["review_pet"])
pet = {r[ph["review_id"]].value: r[ph["name"]].value for r in prows}
species = {r[ph["review_id"]].value: r[ph["species"]].value for r in prows}
pch, pprows = tbl(wb["products"])
pcat = {r[pch["id"]].value: r[pch["category_code"]].value for r in pprows}
concern = {}
for r in crows:
    concern.setdefault(r[ch["review_id"]].value, set()).add(r[ch["concern_code"]].value)
q = {(r[qh["review_id"]].value, r[qh["review_question_type"]].value): r[qh["review_answer"]] for r in qrows}

stat = {t: [0, 0] for t in OPTIONAL}
for r in rrows:
    rid, star = r[rh["id"]].value, r[rh["star_rate"]].value
    # 사용 기간은 폼에서 자유 입력(일 단위) -> 둥근 숫자 40% + 로그정규 분포 60%
    usage = int(pick(ROUND_DAYS)) if RNG.random() < .4 else int(np.clip(round(RNG.lognormal(np.log(18), .8)), 3, 120))
    r[rh["usage_period"]].value = usage
    tags = concern.get(rid, set())
    name = pet[rid]
    sp = SP[species[rid]]
    cat = pcat[r[rh["product_id"]].value]
    low_main = main_issue(r[rh["text"]].value) if star <= 3 else None
    if star <= 3 and r[rh["text"]].value.startswith(name + "이 "):  # "루이이" -> "루이가" 조사 보정
        r[rh["text"]].value = josa(name, "이", "가") + r[rh["text"]].value[len(name) + 1:]
    answered = {}
    if star <= 3 and q[(rid, "ALLERGY")].value == "NEUTRAL":  # 알러지는 없었어요(POSITIVE)/있었어요(NEGATIVE)만 존재
        q[(rid, "ALLERGY")].value = "POSITIVE"
    if star >= 4:
        fc = q[(rid, "FEEDING_CONVENIENCE")]
        fc.value = "POSITIVE" if RNG.random() < P_POS["FEEDING_CONVENIENCE"] else "NEUTRAL"
        answered["FEEDING_CONVENIENCE"] = fc.value
    for t in OPTIONAL:
        related = bool(tags & CONCERN[t])
        p = .9 if related else FILL[t] * (.5 if (t in SLOW and usage < 14) else 1)
        keep = RNG.random() < p or t == low_main
        cell = q[(rid, t)]
        if star >= 4:
            if keep:
                pp = P_POS[t] + (.25 if related and t != "ALLERGY" else 0)
                cell.value = "POSITIVE" if RNG.random() < pp else "NEUTRAL"
        if not keep:
            cell.value = None
        if cell.value is not None:
            answered[t] = cell.value
        stat[t][0] += 1; stat[t][1] += cell.value is not None
    S, T = josa(name, "이", "가"), josa(name, "은", "는")
    mode = MODES[RNG.choice(3, p=[m[0] for m in MODES])]
    ctx = pick(CTX[cat]).format(sp=sp) if RNG.random() < mode[1] else None
    use = pick(USAGE).format(u=usage) if RNG.random() < mode[2] else None
    if star >= 4:  # 본문 재작성 (쿠팡 후기 스타일, 길이는 단문/중문/장문 혼합)
        pos = q[(rid, "PALATABILITY")].value == "POSITIVE"
        pal = pick(PAL_POS[cat] if pos else PAL_NEU).format(s=S, t=T)
        ments = []
        for t in RNG.permutation(OPTIONAL + ["FEEDING_CONVENIENCE"]):
            if t in answered and answered[t] in ("POSITIVE", "NEUTRAL"):
                if RNG.random() < (.9 if tags & CONCERN[t] else mode[3]):
                    m = pick(MENTION[(t, answered[t])]) + "."
                    if t in SLOW and usage < 14 and answered[t] == "POSITIVE":
                        m = "아직 며칠 안 됐지만 " + m
                    ments.append(m)
        extra = " ".join(RNG.choice(EXTRA, 2 if mode[4] == 1.0 else 1, replace=False)) if RNG.random() < mode[4] else None
        story = pick(STORY if pos else STORY_NEU) if RNG.random() < mode[5] else None
        tip = pick(TIP).format(sp=sp) if RNG.random() < mode[5] * .7 else None
        close = pick(CLOSE5 if (pos and star == 5) else CLOSE4 if pos else CLOSE_NEU)
        while True:
            text = " ".join(x for x in [ctx, story, use, pal, *ments, tip, extra, close] if x)
            if len(text) <= 255:
                break
            if tip: tip = None
            elif extra: extra = None
            elif story: story = None
            elif ctx: ctx = None
            elif ments: ments.pop()
            else: use = None
        if RNG.random() < .25:
            text = text[:-1] + pick([" ㅎㅎ", "^^", "!!"]) if text.endswith(".") else text
        r[rh["text"]].value = text
    else:  # 1~3점: 기존 핵심 문장(도입/불만/마무리)은 유지하고 맥락·사용기간·부가 문장만 덧붙임
        parts = re.split(r"(?<=\.) ", r[rh["text"]].value)
        assert len(parts) == 3, parts
        extra = pick(EXTRA_LOW[star]) if RNG.random() < max(.5, mode[4]) else None
        story = pick(STORY_LOW[star]) if RNG.random() < mode[5] else None
        r[rh["text"]].value = " ".join(x for x in [ctx, story, use, parts[0], parts[1], extra, parts[2]] if x)
        assert len(r[rh["text"]].value) <= 255

rs.cell(rs.max_row + 1, 1, MARK)
rs.cell(rs.max_row, 2, "기호성(PALATABILITY)·급여 편의성(FEEDING_CONVENIENCE)만 필수 응답, 나머지 4개 문항은 선택이라 일부 리뷰는 "
        "review_answer NULL (리뷰당 6행은 유지). 알러지는 없었어요=POSITIVE / 있었어요=NEGATIVE. 본문에 언급된 항목은 모두 응답이 있는 항목")
wb.save(PATH)
for t, (n, a) in stat.items():
    print(f"{t:22s} 응답률 {a / n:.0%}")
