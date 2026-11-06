import os
import datetime
import re
import json
import random
import feedparser
import requests
from openai import OpenAI

# 💡 1. 전 세계 반도체 밸류체인 거점 현지 언어/국가 뉴스 검색 극한 확장
RSS_FEEDS = {
    '한국(메모리)': 'https://news.google.com/rss/search?q=반도체+공정+OR+수율+when:1d&hl=ko&gl=KR',
    '미국(설계/장비)': 'https://news.google.com/rss/search?q=semiconductor+OR+Intel+OR+Applied+Materials+when:1d&hl=en&gl=US',
    '대만(TSMC/파운드리)': 'https://news.google.com/rss/search?q=半導體+OR+台積電+when:1d&hl=zh-TW&gl=TW',
    '중국(SMIC/굴기)': 'https://news.google.com/rss/search?q=半导体+OR+中芯国际+OR+光刻机+when:1d&hl=zh-CN&gl=CN',
    '일본(소재/EUV)': 'https://news.google.com/rss/search?q=半導体+OR+東京エレクトロン+OR+信越化学+when:1d&hl=ja&gl=JP',
    'Nature나노테크': 'https://www.nature.com/nnano.rss'
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

def collect_arxiv_papers():
    papers = []
    print("  -> arXiv 최신 학술 논문 검색 중...")
    try:
        url = 'http://export.arxiv.org/api/query?search_query=all:"semiconductor"+AND+(all:"lithography"+OR+all:"etching"+OR+all:"deposition")&sortBy=submittedDate&sortOrder=desc&max_results=2'
        res = requests.get(url, timeout=5)
        feed = feedparser.parse(res.content)
        for entry in feed.entries:
            summary = getattr(entry, 'summary', '')[:200].replace('\n', ' ')
            papers.append(f"[arXiv 논문] {entry.title} (요약: {summary}...)")
    except Exception as e:
        pass
    return papers

def collect_news():
    articles = []
    print("[1/4] 전 세계 5대 거점 외신 및 저널 데이터 수집 중...")
    
    for source, url in RSS_FEEDS.items():
        try:
            res = requests.get(url, headers=HEADERS, timeout=5)
            res.raise_for_status()
            feed = feedparser.parse(res.content)
            # 국가별 상위 3개씩 추출 (다국어 데이터 폭증 방지)
            for entry in feed.entries[:3]: 
                articles.append(f"[{source}] {getattr(entry, 'title', '')}")
        except:
            pass
            
    arxiv_data = collect_arxiv_papers()
    articles.extend(arxiv_data)
    
    return articles

def generate_blog_content(articles):
    print("[2/4] STEP 1: 글로벌 다국어 데이터 분석 및 3단 기획 중...")
    api_key = os.environ.get("OPENAI_API_KEY")
    client = OpenAI(api_key=api_key)
    raw_text = "\n".join(articles)
    
    outline_system = "당신은 미국, 대만, 중국, 일본의 반도체 산업 동향과 최전선 학술 논문을 융합 분석하는 시니어 애널리스트 및 연구원입니다."
    outline_user = f"""
    아래 수집된 5개국 외신, Nature 저널, arXiv 최신 논문 데이터를 융합 분석하여 가장 핫한 메인 테마 1개를 잡고 JSON으로 출력하세요.
    
    {{
        "title": "다국어 동향과 기술/논문을 아우르는 매력적인 리포트 제목",
        "keyword": "썸네일용 영문 검색어 1개 (예: silicon wafer)",
        "outline": [
            "1. 🌍 글로벌 반도체 지정학 및 시장 동향 (중국/대만/미국/일본의 동향 포함)",
            "2. 🔬 최전선 기술 분석: 관련 논문 및 공정 딥다이브",
            "3. 💡 향후 전망 및 엔지니어의 시사점"
        ]
    }}
    
    수집된 데이터(영어/중국어/일본어/한국어 혼합):
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
    
    print(f"[3/4] STEP 2: 문맥 이어달리기 방식으로 본문 심층 작성 중...")
    full_content = ""
    
    writer_system = """
    당신은 화학공학 전공 반도체 공정 엔지니어입니다. 해외 다국어 데이터를 한국어로 유창하게 분석하여 설명합니다.
    [규칙]
    1. 수식은 HTML 태그(<sub>, <sup>, &rarr;)만 사용. (LaTeX 금지)
    2. 마크다운 표(Table) 또는 Mermaid 다이어그램 적극 활용.
    3. 사진 삽입 절대 금지.
    4. 🚨 절대 금지어: '결론적으로', '요약하자면', '종합하면'.
    """

    for i, section_title in enumerate(sections):
        if i == 0:
            role_guide = "리포트의 '서론'입니다. 중국, 대만, 일본 등의 외신 데이터를 기반으로 거시적 동향을 설명하세요. 결론을 내리지 마세요."
        elif i == len(sections) - 1:
            role_guide = "리포트의 '결론'입니다. 지정학적 시장 전망과 엔지니어로서의 통찰을 제시하세요."
        else:
            role_guide = "리포트의 '본론(딥다이브)'입니다. 서론/결론 없이 논문이나 기술적 팩트만 깊게 파고드세요."

        writer_user = f"""
        전체 리포트 주제: {title}
        현재 작성해야 할 섹션: ## {section_title}
        작성 지침: {role_guide}
        
        [지금까지 작성된 앞부분 내용]
        {full_content if full_content else "없음 (이제 시작함)"}
        
        위 내용과 매끄럽게 이어지도록, 본문만 매우 전문적으로 작성하세요.
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
    print(f"[4/4] 메인 썸네일 적용 및 파일 생성 중...")
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
tags: [글로벌이슈, 해외외신, 공정기술, 시장전망]
image:
  path: "{header_image}"
math: true
mermaid: true
---

> **💡 전 세계 주요 5개국(한·미·중·일·대만)의 최신 동향과 학술 논문을 융합 분석한 글로벌 리포트입니다.**

"""
    os.makedirs("_posts", exist_ok=True)
    with open(filename, "w", encoding="utf-8") as f:
        f.write(front_matter + content)
    print("✅ 글로벌 일일 브리핑 리포트 생성 완료")

def main():
    print("=== 다국어 뉴스 & 논문 브리핑 자동화 시작 ===")
    articles = collect_news()
    if articles:
        title, keyword, content = generate_blog_content(articles)
        save_to_markdown(title, keyword, content)

if __name__ == "__main__":
    main()
