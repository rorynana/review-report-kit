// 올리브영 리뷰 수집 키트
// 사용법: node collect.js <상품 페이지 주소> [건수]
// 평소 크롬을 새 프로필로 따로 켜고 거기에 붙어서, 상품 페이지 안에서 리뷰를 불러온다.
// 도움순 N건 + 별점 낮은순 N건, 겹치면 한 번만. 결과는 실행한 폴더의 reviews.csv.
// 제품 전체 별점 분포·리뷰 수, 올리브영 AI 요약, 제품명·대표 이미지는 oliveyoung.json.
const puppeteer = require('puppeteer-core');
const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');
const os = require('os');
const net = require('net');

const url = process.argv[2];
const TARGET = parseInt(process.argv[3] || '100', 10);
const m = url && url.match(/goodsNo=([A-Z0-9]+)/);
if (!m) {
  console.error('상품 페이지 주소를 넣어 주세요. 예: node collect.js "https://www.oliveyoung.co.kr/store/goods/getGoodsDetail.do?goodsNo=A000000258792"');
  process.exit(1);
}
const GOODS_NO = m[1];
const PAGE_URL = `https://www.oliveyoung.co.kr/store/goods/getGoodsDetail.do?goodsNo=${GOODS_NO}`;
const API_URL = 'https://m.oliveyoung.co.kr/review/api/v2/reviews/cursor';
const SORTS = [['USEFUL_SCORE_DESC', '도움순'], ['RATING_ASC', '별점 낮은순']];
const PAGE_SIZE = 10, DELAY_MS = 1000;
const SKIN = { A01: '지성', A02: '건성', A03: '복합성', A04: '민감성', A05: '약건성', A06: '트러블성', A07: '중성' };
const sleep = ms => new Promise(r => setTimeout(r, ms));

function findChrome() {
  const c = [
    process.env.CHROME_PATH,
    'C:/Program Files/Google/Chrome/Application/chrome.exe',
    'C:/Program Files (x86)/Google/Chrome/Application/chrome.exe',
    path.join(process.env.LOCALAPPDATA || '', 'Google/Chrome/Application/chrome.exe'),
    '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
    '/usr/bin/google-chrome',
  ].filter(Boolean);
  const hit = c.find(p => fs.existsSync(p));
  if (!hit) throw new Error('크롬을 찾지 못했습니다. 크롬을 설치하거나 CHROME_PATH 에 경로를 넣어 주세요.');
  return hit;
}

function freePort() {
  return new Promise(res => { const s = net.createServer(); s.listen(0, () => { const p = s.address().port; s.close(() => res(p)); }); });
}

async function blocked(page) {
  const t = await page.title().catch(() => '');
  const h = await page.content().catch(() => '');
  return /잠시만|Just a moment/i.test(t) || /challenge-platform|cf-turnstile/i.test(h);
}

(async () => {
  const chrome = findChrome();
  const port = await freePort();
  const profile = fs.mkdtempSync(path.join(os.tmpdir(), 'oy-kit-'));
  const proc = spawn(chrome, [`--remote-debugging-port=${port}`, `--user-data-dir=${profile}`,
    '--no-first-run', '--no-default-browser-check', 'about:blank'], { stdio: 'ignore' });
  let browser;
  for (let i = 0; i < 30 && !browser; i++) {
    await sleep(500);
    browser = await puppeteer.connect({ browserURL: `http://127.0.0.1:${port}`, defaultViewport: null }).catch(() => null);
  }
  if (!browser) throw new Error('크롬에 붙지 못했습니다.');
  try {
    const page = (await browser.pages())[0] || await browser.newPage();
    await page.goto(PAGE_URL, { waitUntil: 'domcontentloaded', timeout: 60000 });
    await sleep(3000);
    if (await blocked(page)) {
      console.log('⚠ 올리브영 확인 화면이 떴습니다. 방금 열린 크롬 창에서 확인 상자를 직접 눌러 주세요. 2분 기다립니다.');
      for (let i = 0; i < 60 && await blocked(page); i++) await sleep(2000);
      if (await blocked(page)) throw new Error('확인 화면을 넘지 못했습니다. 강사에게 알려 주세요.');
      console.log('통과했습니다. 이어서 모읍니다.');
    }
    await sleep(DELAY_MS);

    const byId = new Map();
    for (const [sortType, label] of SORTS) {
      let got = 0, cursor = null;
      for (let p = 0; got < TARGET; p++) {
        const body = { goodsNumber: GOODS_NO, size: PAGE_SIZE, sortType, reviewType: 'ALL', ...(cursor || { page: 0 }) };
        const res = await page.evaluate(async (u, b) => {
          const r = await fetch(u, { method: 'POST', headers: { 'content-type': 'application/json', accept: 'application/json, text/plain, */*' }, body: JSON.stringify(b) });
          return { status: r.status, json: r.ok ? await r.json() : null };
        }, API_URL, body);
        if (res.status !== 200 || !res.json) throw new Error(`${label} ${p + 1}쪽: HTTP ${res.status}`);
        const d = res.json.data || {};
        const list = d.goodsReviewList || [];
        if (!list.length) break;
        for (const rv of list.slice(0, TARGET - got)) {
          const prev = byId.get(rv.reviewId);
          if (prev) { if (!prev.sorts.includes(label)) prev.sorts.push(label); continue; }
          byId.set(rv.reviewId, { rv, sorts: [label] });
        }
        got += Math.min(list.length, TARGET - got);
        console.log(`${label} ${p + 1}쪽: 누적 ${got}건`);
        await sleep(DELAY_MS);
        if (!d.hasNext) break;
        cursor = { cursorId: d.nextCursorId, cursorScore: d.nextCursorScore, cursorCount: d.nextCursorCount };
      }
    }

    // 제품 전체 수치: 별점 분포·총 리뷰 수, 올리브영 AI 요약, 제품명·대표 이미지
    const getJson = u => page.evaluate(async x => { try { const r = await fetch(x); return r.ok ? await r.json() : null; } catch { return null; } }, u);
    const st = (await getJson(`https://m.oliveyoung.co.kr/review/api/v2/reviews/${GOODS_NO}/stats`))?.data || {};
    await sleep(DELAY_MS);
    const sm = (await getJson(`https://m.oliveyoung.co.kr/review/api/v1/reviews/${GOODS_NO}/summary`))?.data || {};
    const rd = st.ratingDistribution || {};
    const dist = {}; for (const x of rd.ratingStatDtos || []) dist[x.rating] = x.percentage;
    const features = []; for (let i = 1; i <= 3; i++) if (sm[`feature${i}Title`]) features.push({ title: sm[`feature${i}Title`], desc: sm[`feature${i}Description`] || '' });
    const meta = await page.evaluate(() => ({
      title: (document.querySelector('meta[property="og:title"]') || {}).content || document.title,
      image: (document.querySelector('meta[property="og:image"]') || {}).content || null }));
    const product = { source: 'oliveyoung', goodsNo: GOODS_NO, url: PAGE_URL, collectedAt: new Date().toISOString().slice(0, 10),
      goodsName: st.goodsName || meta.title, image: meta.image,
      totalReviewCount: st.reviewCount ?? null, avgRating: rd.averageRating ?? null, ratingDistributionPct: dist,
      aiSummary: { positiveRatio: sm.positiveRatio ?? null, negativeRatio: sm.negativeRatio ?? null, features } };
    fs.writeFileSync(path.join(process.cwd(), 'oliveyoung.json'), JSON.stringify(product, null, 2), 'utf8');
    console.log(`제품: ${product.goodsName} / 전체 ★${product.avgRating} / 리뷰 ${product.totalReviewCount}건 / AI 요약 긍정 ${product.aiSummary.positiveRatio}%`);

    const esc = v => { const s = String(v ?? ''); return /[",\r\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s; };
    const yn = b => (b ? 'Y' : 'N');
    const rows = [['별점', '작성일', '피부 타입', '재구매 여부', '한 달 이상 사용 여부', '본문', '정렬']];
    for (const { rv, sorts } of byId.values()) {
      const code = rv.profileDto?.skinType;
      rows.push([rv.reviewScore, rv.createdDateTime, SKIN[code] || code || '', yn(rv.isRepurchase),
        yn(rv.isMonthUseReview || rv.isMonthOverReview), rv.content, sorts.join('|')]);
    }
    const out = path.join(process.cwd(), 'reviews.csv');
    fs.writeFileSync(out, '\uFEFF' + rows.map(r => r.map(esc).join(',')).join('\r\n') + '\r\n', 'utf8');
    console.log(`✅ 저장: ${out} (${rows.length - 1}건)`);
  } finally {
    await browser.close().catch(() => {});   // 이 키트가 켠 크롬만 닫는다
    try { proc.kill(); } catch {}
    try { fs.rmSync(profile, { recursive: true, force: true }); } catch {}
  }
})().catch(e => { console.error('❌ ' + e.message); process.exit(1); });
