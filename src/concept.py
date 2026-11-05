import os
import datetime
import re
import json
import random
import requests
from openai import OpenAI

FALLBACK_IMAGES = ["https://images.unsplash.com/photo-1531297484001-80022131f5a1?auto=format&fit=crop&w=1200&h=675&q=80"]

def get_dynamic_image(keyword):
    """💡 Unsplash API 썸네일 검색"""
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
    concepts = set() 
    if not os.path.exists("_posts"): return []
    for filename in os.listdir("_posts"):
        if filename.endswith(".md"):
            with open(os.path.join("_posts", filename), "r", encoding="utf-8") as f:
                content = f.read()
                if "series: 반도체 핵심 공정 백과사전" in content:
                    title_match = re.search(r'title:\s*"(.*?)"', content)
                    if title_match:
                        clean_title = title_match.group(1).replace("[반도체 백과사전]", "").strip()
                        concepts.add(clean_title)
    return list(concepts)

def generate_concept_wiki(previous_topics):
    api_key = os.environ.get("OPENAI_API_KEY")
    client = OpenAI(api_key=api_key)
    prev_topics_str = "\n".join([f"- {t}" for t in previous_topics]) if previous_topics else "기록 없음."
    
    # ==========================================
    # [STEP 1] 주제 선정 및 목차(Outline) 기획
    # ==========================================
    print("[1/4] STEP 1: 새로운 주제 선정 및 뼈대(Outline) 기획 중...")
    
    outline_system = "당신은 화학공학 전공 테크 위키 수석 에디터입니다. 겹치지 않는 새로운 심화 공정 기술을 하나 선정하고 구조를 기획하세요."
    outline_user = f"""
    [🚨 이미 작성된 주제 목록 - 중복 금지]
    {prev_topics_str}
    
    위 목록에 없는 '새로운 반도체 심화 공정 개념' 1가지를 선정하여 아래 JSON 양식으로 출력하세요.
    
    {{
        "title": "주제명 (예: 원자층 증착(ALD) 공정)",
        "keyword": "썸네일용 영문 검색어 1개 (예: semiconductor)",
        "outline": [
            "1. 개념 개요 및 등장 배경",
            "2. 핵심 작동 원리 (화학적 메커니즘)",
            "3. 주요 소재 및 공정 파라미터",
            "4. 기술적 한계점 및 향후 전망"
        ]
    }}
    """
    
    res_outline = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "system", "content": outline_system}, {"role": "user", "content": outline_user}],
        response_format={"type": "json_object"},
        temperature=0.6
    )
    
    plan = json.loads(res_outline.choices[0].message.content)
    clean_title = plan["title"]
    final_title = f"[반도체 백과사전] {clean_title}"
    keyword = plan["keyword"]
    sections = plan["outline"]
    
    # ==========================================
    # [STEP 2] 분할 프롬프팅: 각 목차별 개별 심층 작성
    # ==========================================
    print(f"[2/4] STEP 2: '{clean_title}' 주제에 대해 {len(sections)}단계 분할 딥다이브 작성 시작...")
    
    full_content = ""
    
    writer_system = """
    당신은 화학공학 전공 시니어 반도체 공정 엔지니어입니다.
    요청받은 단일 섹션(목차)에 대해서만 극도로 깊고 상세하게(최소 1,500자 이상) 논문/위키 수준으로 분석하세요.
    [규칙]
    1. 수식은 LaTeX 금지, HTML 태그(<sub>, <sup>, &rarr;)만 사용.
    2. 내용 설명 중 적절한 곳에 마크다운 표(Table) 또는 Mermaid 다이어그램을 활용하여 전문성을 높이세요.
    3. 사진(이미지) 삽입은 절대 금지합니다.
    """

    for i, section_title in enumerate(sections):
        print(f"  -> ({i+1}/{len(sections)}) '{section_title}' 섹션 작성 중...")
        
        writer_user = f"""
        전체 문서 주제: {clean_title}
        현재 작성해야 할 섹션: ## {section_title}
        
        오직 이 섹션에 해당하는 내용만 아주 길고 전문적으로 작성하세요. 서론이나 결론을 억지로 덧붙이지 말고 해당 파트의 본문만 순수 텍스트(마크다운)로 출력하세요.
        """
        
        res_section = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": writer_system}, {"role": "user", "content": writer_user}],
            temperature=0.5
        )
        
        section_content = res_section.choices[0].message.content.strip()
        
        # 합치기
        full_content += f"## {section_title}\n\n{section_content}\n\n---\n\n"

    return final_title, keyword, full_content

def save_to_markdown(title, keyword, content):
    print(f"[3/4] 맞춤형 썸네일({keyword}) 검색 및 파일 생성 중...")
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

> **💡 {title}에 대한 심층 분석 문서입니다.**

"""
    os.makedirs("_posts", exist_ok=True)
    with open(filename, "w", encoding="utf-8") as f:
        f.write(front_matter + content)
    print(f"[4/4] ✅ 분할 프롬프트 기반 초장문 위키 생성 완료: {title}")

def main():
    print("=== 분할 프롬프트 기반 위키 자동화 시작 ===")
    prev_topics = get_previous_concepts()
    title, keyword, content = generate_concept_wiki(prev_topics)
    save_to_markdown(title, keyword, content)

if __name__ == "__main__":
    main()
