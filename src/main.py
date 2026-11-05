import os
import datetime
import re
import json
import random
import feedparser
import requests
from openai import OpenAI

RSS_FEEDS = {
    '반도체이슈': 'https://news.google.com/rss/search?q=반도체+동향+OR+투자+OR+수율+when:1d&hl=ko&gl=KR&ceid=KR:ko',
    '공정/소재': 'https://news.google.com/rss/search?q=반도체+공정+OR+소재+OR+EUV+when:1d&hl=ko&gl=KR&ceid=KR:ko'
}
HEADERS = {'User-Agent': 'Mozilla/5.0'}
FALLBACK_IMAGES = ["https://images.unsplash.com/photo-1518770660439-4636190af475?auto=format&fit=crop&w=1200&h=675&q=80"]

def get_dynamic_image(keyword):
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

def collect_news():
    articles = []
    print("[1/4] 최신 반도체 이슈 수집 중...")
    for source, url in RSS_FEEDS.items():
        try:
            res = requests.get(url, headers=HEADERS, timeout=5)
            res.raise_for_status()
            feed = feedparser.parse(res.content)
            for entry in feed.entries[:8]: 
                articles.append(f"[{source}] {getattr(entry, 'title', '')}")
        except:
            pass
    return articles

def generate_blog_content(articles):
    print("[2/4] STEP 1: 기사 분석 및 리포트 뼈대(Outline) 기획 중...")
    api_key = os.environ.get("OPENAI_API_KEY")
    client = OpenAI(api_key=api_key)
    raw_text = "\n".join(articles)
    
    outline_system = "당신은 반도체 산업 트렌드와 기술을 분석하는 시니어 애널리스트/공정 엔지니어입니다."
    outline_user = f"""
    아래 수집된 오늘자 기사들을 분석하여, 가장 핫한 이슈 1개를 메인 테마로 잡고 리포트 구조를 JSON으로 출력하세요.
    
    {{
        "title": "오늘의 핫이슈를 담은 매력적인 리포트 제목 (예: TSMC 2나노 수율 논란과 GAA 공정 한계)",
        "keyword": "썸네일용 영문 검색어 1개 (예: silicon wafer)",
        "outline": [
            "1. 📰 오늘의 핫이슈 (뉴스 요약 및 배경)",
            "2. 🔬 엔지니어의 시선: 기술 분석 (공정/소재 원리 딥다이브)",
            "3. 💡 향후 전망 및 시사점 (시장 파급력)"
        ]
    }}
    
    기사 목록:
    {raw_text}
    """
    
    res_outline = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "system", "content": outline_system}, {"role": "user", "content": outline_user}],
        response_format={"type": "json_object"},
        temperature=0.6
    )
    
    plan = json.loads(res_outline.choices[0].message.content)
    title = f"[일일브리핑] {plan['title']}"
    keyword = plan["keyword"]
    sections = plan["outline"]
    
    print(f"[3/4] STEP 2: 문맥 이어달리기(Context Chaining) 방식으로 본문 심층 작성 중...")
    full_content = ""
    
    writer_system = """
    당신은 화학공학 전공 반도체 공정 엔지니어입니다.
    [규칙]
    1. 수식은 LaTeX 금지, HTML 태그(<sub>, <sup>, &rarr;)만 사용.
    2. 내용 설명 중 적절한 곳에 마크다운 표(Table) 또는 Mermaid 다이어그램을 활용하세요.
    3. 사진(이미지) 삽입은 절대 금지합니다.
    """

    for i, section_title in enumerate(sections):
        # 💡 [핵심] 섹션 위치에 따른 역할 부여 (결론 남발 방지)
        if i == 0:
            role_guide = "이 부분은 리포트의 '서론'입니다. 이슈의 배경과 현황을 몰입감 있게 설명하세요. 절대 결론이나 요약을 내지 마세요."
        elif i == len(sections) - 1:
            role_guide = "이 부분은 리포트의 '결론'입니다. 앞선 기술 분석을 바탕으로 시장의 전망과 인사이트를 종합하세요."
        else:
            role_guide = "이 부분은 리포트의 '본론(딥다이브)'입니다. 서론이나 결론을 억지로 적지 마세요. '결론적으로', '요약하자면' 같은 표현은 엄격히 금지됩니다. 오직 기술적 팩트와 원리만 깊게 파고드세요."

        writer_user = f"""
        전체 리포트 주제: {title}
        현재 작성해야 할 섹션: ## {section_title}
        작성 지침: {role_guide}
        
        [지금까지 작성된 앞부분 내용]
        {full_content if full_content else "없음 (이제 시작함)"}
        
        위 앞부분 내용과 물 흐르듯 자연스럽게 이어지도록, 현재 섹션(## {section_title})에 해당하는 본문만 아주 길고 전문적으로 작성하세요.
        """
        
        res_section = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": writer_system}, {"role": "user", "content": writer_user}],
            temperature=0.5
        )
        
        section_content = res_section.choices[0].message.content.strip()
        full_content += f"## {section_title}\n\n{section_content}\n\n---\n\n"

    return title, keyword, full_content

def save_to_markdown(title, keyword, content):
    print(f"[4/4] 썸네일({keyword}) 적용 및 파일 생성 중...")
    content = content.replace('\\', '\\\\')
    now = datetime.datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    safe_title = re.sub(r'[^가-힣A-Za-z0-9\s]', '', title).strip().replace(' ', '-')
    filename = f"_posts/{date_str}-{safe_title}.md"
    
    header_image = get_dynamic_image(keyword)
    front_matter = f"""---
title: "{title}"
date: {now.strftime("%Y-%m-%d %H:%M:%S +0900")}
categories: [반도체 브리핑, 트렌드 동향]
tags: [반도체이슈, 공정기술, 시장전망]
image:
  path: "{header_image}"
math: true
mermaid: true
---

> **💡 오늘의 반도체 핵심 이슈와 기술적 인사이트를 정리한 리포트입니다.**

"""
    os.makedirs("_posts", exist_ok=True)
    with open(filename, "w", encoding="utf-8") as f:
        f.write(front_matter + content)
    print("✅ 일일 브리핑 리포트 생성 완료")

def main():
    print("=== 뉴스 브리핑 다중 생성 자동화 시작 ===")
    articles = collect_news()
    if articles:
        title, keyword, content = generate_blog_content(articles)
        save_to_markdown(title, keyword, content)

if __name__ == "__main__":
    main()
