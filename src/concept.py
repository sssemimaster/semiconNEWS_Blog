import os
import datetime
import re
import random
import requests
from openai import OpenAI

FALLBACK_IMAGES = ["https://images.unsplash.com/photo-1531297484001-80022131f5a1?auto=format&fit=crop&w=1200&h=675&q=80"]

def get_dynamic_image(keyword):
    """💡 AI가 지정한 맞춤형 키워드로 관련성 높은 썸네일 검색"""
    api_key = os.environ.get("UNSPLASH_API_KEY")
    if not api_key or not keyword:
        return random.choice(FALLBACK_IMAGES)
    try:
        url = f"https://api.unsplash.com/photos/random?query={keyword}&client_id={api_key}"
        res = requests.get(url, timeout=5)
        res.raise_for_status()
        data = res.json()
        return data['urls']['raw'] + "&w=1200&h=675&fit=crop&q=80"
    except:
        return random.choice(FALLBACK_IMAGES)

def get_previous_concepts():
    """💡 역대 작성된 모든 백과사전 주제를 100% 긁어옵니다."""
    concepts = set() 
    if not os.path.exists("_posts"): return []
    
    for filename in os.listdir("_posts"):
        if filename.endswith(".md"):
            with open(os.path.join("_posts", filename), "r", encoding="utf-8") as f:
                content = f.read()
                if "series: 반도체 핵심 공정 백과사전" in content:
                    title_match = re.search(r'title:\s*"(.*?)"', content)
                    if title_match:
                        # "[반도체 백과사전]" 꼬리표를 떼고 순수 주제명만 추출하여 기록
                        clean_title = title_match.group(1).replace("[반도체 백과사전]", "").strip()
                        concepts.add(clean_title)
                        
    return list(concepts)

def generate_concept_wiki(previous_topics):
    print("[1/3] 내용 중심 구조적 위키 문서 생성 중...")
    api_key = os.environ.get("OPENAI_API_KEY")
    client = OpenAI(api_key=api_key)
    prev_topics_str = "\n".join([f"- {t}" for t in previous_topics]) if previous_topics else "기록 없음."
    
    system_prompt = """
    당신은 화학공학 전공 테크 위키 작성자입니다.
    
    [시각화 및 딥다이브 규칙]
    1. 사진(이미지) 삽입은 절대 금지합니다.
    2. 정보량이 방대하게 느껴지도록 텍스트 길이를 최소 4,000자 이상으로 매우 상세히 늘려 쓰세요.
    3. 기술의 이해를 돕기 위해 아래 시각화 기법을 2~3회 이상 사용하세요.
       - Mermaid 다이어그램: 공정 플로우, 메커니즘을 `mermaid` 코드 블록으로 구조화.
       - 마크다운 표(Table): 화학 물질 특성, 공정 스펙 비교표.
    4. 수식은 LaTeX 금지, HTML 태그(<sub>, <sup>, &rarr;)만 사용하세요.
    """

    user_prompt = f"""
    반드시 아래 양식의 순수 텍스트로만 출력하세요.
    
    Title: (여기에 선정한 핵심 주제명만 구체적으로 작성하세요. 예: 원자층 증착(ALD) 공정의 화학적 메커니즘)
    Image_Keyword: (주제에 맞는 Unsplash 검색용 영어 단어 1~2개, 예: lithography, etching, chemistry)
    Content:
    [인용구 요약, 딥다이브 원리(Mermaid, 표 적극 활용), 한계 및 전망으로 구성된 본문]

    [🚨 이미 작성된 위키 주제 목록 - 절대 중복 금지 🚨]
    {prev_topics_str}
    
    위 목록에 있는 주제는 물론이고, 약자/동의어도 절대 중복해서 쓰지 마세요.
    반드시 위 목록에 없는 완전히 새로운 심화 공정 개념 1가지를 정하여 작성하세요.
    """

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
        temperature=0.6 
    )
    
    full_text = response.choices[0].message.content
    try:
        # AI가 작성한 제목을 가져옵니다.
        raw_title = re.search(r'Title:\s*(.*)', full_text, re.IGNORECASE).group(1).strip()
        keyword = re.search(r'Image_Keyword:\s*(.*)', full_text, re.IGNORECASE).group(1).strip()
        content = re.search(r'Content:\s*(.*)', full_text, re.IGNORECASE | re.DOTALL).group(1).strip()
        
        # 💡 AI가 말머리를 스스로 달았을 경우 떼어내고, 파이썬이 강제로 [반도체 백과사전]을 붙입니다.
        clean_title = raw_title.replace('[반도체 백과사전]', '').strip()
        title = f"[반도체 백과사전] {clean_title}"
        
    except:
        title = f"[반도체 백과사전] {datetime.datetime.now().strftime('%m월 %d일')} 새로운 공정 딥다이브"
        keyword = "semiconductor manufacturing"
        content = full_text
        
    return title, keyword, content

def save_to_markdown(title, keyword, content):
    print(f"[2/3] 맞춤형 썸네일({keyword}) 검색 및 파일 생성 중...")
    
    content = content.replace('\\', '\\\\')
    
    now = datetime.datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    safe_title = re.sub(r'[^가-힣A-Za-z0-9\s]', '', title).strip().replace(' ', '-')
    filename = f"_posts/{date_str}-wiki-{safe_title}.md"
    
    header_image = get_dynamic_image(keyword)
    
    front_matter = f"""---
title: "{title}"
date: {now.strftime("%Y-%m-%d %H:%M:%S +0900")}
categories: [반도체 백과사전, 공정기술]
tags: [반도체위키, 8대공정, 딥다이브]
series: 반도체 핵심 공정 백과사전
image:
  path: "{header_image}"
math: true
mermaid: true
---

"""
    os.makedirs("_posts", exist_ok=True)
    with open(filename, "w", encoding="utf-8") as f:
        f.write(front_matter + content)
    print(f"✅ 위키 파일 생성 완료: {title}")

def main():
    print("=== 위키 스크립트 시작 ===")
    prev_topics = get_previous_concepts()
    title, keyword, content = generate_concept_wiki(prev_topics)
    save_to_markdown(title, keyword, content)

if __name__ == "__main__":
    main()
