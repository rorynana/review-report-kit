// 화해 수집: node collect-hwahae.js "제품명"   (화해 goodsId 숫자를 넣어도 된다)
// 평소 크롬을 새 프로필로 따로 켜고 거기에 붙어서, 화해 상품 페이지의 키워드 집계(좋아요·아쉬워요),
// 별점, 랭킹, 전성분을 읽는다. 결과는 실행한 폴더의 hwahae.json.
const puppeteer = require('puppeteer-core');
const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');
const os = require('os');
const net = require('net');
const sleep = ms => new Promise(r => setTimeout(r, ms));

const query = process.argv[2];
if (!query) { console.error('제품명을 넣어 주세요. 예: node collect-hwahae.js "토니모리 세라마이드 모찌 토너"'); process.exit(1); }

function findChrome() {
  const c = [process.env.CHROME_PATH, 'C:/Program Files/Google/Chrome/Application/chrome.exe',
    'C:/Program Files (x86)/Google/Chrome/Application/chrome.exe',
    path.join(process.env.LOCALAPPDATA || '', 'Google/Chrome/Application/chrome.exe'),
    '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', '/usr/bin/google-chrome'].filter(Boolean);
  const hit = c.find(p => fs.existsSync(p));
  if (!hit) throw new Error('크롬을 찾지 못했습니다. 크롬을 설치하거나 CHROME_PATH 에 경로를 넣어 주세요.');
  return hit;
}
function freePort() {
  return new Promise(res => { const s = net.createServer(); s.listen(0, () => { const p = s.address().port; s.close(() => res(p)); }); });
}

const EXTRACT = () => {
  const out = { productName: (document.title || '').split('|')[0].trim() };
  let pp = null;
  try { pp = JSON.parse(document.getElementById('__NEXT_DATA__').textContent).props.pageProps; } catch (e) { out.ssrError = String(e); }

  if (pp) {
    const pair = pp.productGoodsPairData || {};
    const common = pair.common || pp.goodsProductsCommonData || {};
    const product = pair.product || {};
    out.productName = product.name || out.productName;
    out.brand = (product.brand || {}).name || null;
    out.rating = (common.avg_ratings !== undefined) ? common.avg_ratings : null;
    out.reviewCount = (common.review_count !== undefined) ? common.review_count : null;
    out.category = ((product.categories || [])[0] || {}).name || null;
    out.rankings = (common.rankings || []).map((r, i) => ({
      rank: (r.rank !== undefined) ? r.rank : null, category: r.category_name, attribute: r.attribute_name || null,
      text: (common.rank_descriptions || [])[i] || null
    })).filter(r => r.rank);
    out.rankTop = (common.rank_descriptions || [])[0] || null;
    const pa = (product.product_attributes || [])[0] || {};
    out.positioning = { primary: (pa.primary_product_attribute || {}).name || null, sub: (pa.product_attributes || []).map(x => x.name) };
    const topic = t => ({ keyword: t.name, count: t.review_count, sentence: t.sentence || null });
    out.positive = (pp.productTopicsPositive || []).map(topic);
    out.negative = (pp.productTopicsNegative || []).map(topic);
    const rs = pp.productReviewSummaryData || {};
    const rr = ((rs.productReviewMetaData || {}).reviewRatings) || null; // [1점,2점,3점,4점,5점]
    if (rr && rr.length === 5) out.ratingDist = { '1': rr[0], '2': rr[1], '3': rr[2], '4': rr[3], '5': rr[4], total: rr.reduce((a, b) => a + b, 0) };
    out.reviewSamples = (rs.reviewList || []).map(r => ({
      rating: r.rating, skinType: r.skinType || null, gender: r.gender || null, age: r.age || r.ageGroup || null,
      good: r.goodText || null, bad: r.badText || null, date: r.modifyTime || null
    }));
    out.reviews = out.reviewSamples.map(r => [r.skinType, r.good, r.bad].filter(Boolean).join('\n')).filter(Boolean);

    // ---- 전성분 ----
    const ii = pp.productIngredientInfoData || {};
    const ings = ii.ingredients || [];
    const band = ewg => {
      if (!ewg) return 'unknown';
      const m = String(ewg).split('_').map(Number).filter(n => !isNaN(n));
      if (!m.length) return 'unknown';
      const mx = Math.max.apply(null, m);
      return mx <= 2 ? 'low' : mx <= 6 ? 'mid' : 'high';
    };
    const SK = { gd: ['건성', 'good'], go: ['지성', 'good'], gs: ['민감성', 'good'], bd: ['건성', 'bad'], bo: ['지성', 'bad'], bs: ['민감성', 'bad'] };
    out.ingredients = ings.map(x => ({
      name: String(x.korean || '').split(',')[0].trim(), fullName: x.korean, english: x.english,
      ewg: x.ewg || null, ewgBand: band(x.ewg), twenty: !!x.is_twenty, twentyDetail: x.twenty_detail || null, allergy: !!x.is_allergy,
      skinType: x.skin_type || null, good: x.skin_remark_good || null, bad: x.skin_remark_bad || null,
      purpose: x.purpose || null, purposes: (x.purposes || []).map(p => p.group_name).filter(Boolean),
      // 향료 판정: 글리세린처럼 기능 목록 끝에 '착향제'가 끼어 있는 다목적 성분은 제외.
      // (주기능이 착향제/향료) 또는 (착향제 기능 + 오일·리모넨·리날룰류 이름) 또는 알레르기 주의성분(향료 알레르겐)만 향료로 본다.
      fragrance: (function () {
        const pu = String(x.purpose || ''); const first = pu.split(',')[0].trim(); const nm = String(x.korean || '');
        return /^(착향제|향료)$/.test(first) || (/착향제|향료/.test(pu) && /오일|리모넨|리날룰|향/.test(nm)) || !!x.is_allergy;
      })(),
      // 자극 판정: 피부타입 코드에 부정(b*)이 있을 때만. (알란토인처럼 good 코드만 있는데 bad 비고가 달린 경우 제외)
      irritant: /(^|;)b[dos]/.test(String(x.skin_type || '')) && !!x.skin_remark_bad,
      limitation: x.limitation || null, forbidden: !!x.forbidden
    }));
    const s = { total: out.ingredients.length, ewgLow: 0, ewgMid: 0, ewgHigh: 0, ewgUnknown: 0, twentyCount: 0, allergyCount: 0,
      fragranceCount: 0, fragranceList: [], allergenList: [], twentyList: [], irritantList: [], purposeGroups: {}, skinGood: {}, skinBad: {} };
    for (const g of (ii.purpose_default_order || [])) s.purposeGroups[g.group_name] = 0;
    const BAND_KEY = { low: 'ewgLow', mid: 'ewgMid', high: 'ewgHigh', unknown: 'ewgUnknown' };
    for (const x of out.ingredients) {
      s[BAND_KEY[x.ewgBand]]++;
      if (x.twenty) { s.twentyCount++; s.twentyList.push(x.name); }
      if (x.allergy) { s.allergyCount++; s.allergenList.push(x.name); }
      if (x.fragrance) { s.fragranceCount++; s.fragranceList.push(x.name + (x.ewg ? ' (EWG ' + x.ewg + ')' : '')); }
      if (x.irritant) s.irritantList.push(x.name + ': ' + x.bad);
      for (const p of x.purposes) s.purposeGroups[p] = (s.purposeGroups[p] || 0) + 1;
      for (const code of String(x.skinType || '').split(';').filter(Boolean)) {
        const m = SK[code]; if (!m) continue;
        const tgt = m[1] === 'good' ? s.skinGood : s.skinBad;
        tgt[m[0]] = (tgt[m[0]] || 0) + 1;
      }
    }
    out.ingredientSummary = s;
  }

  // ---- 폴백: SSR 없으면 구버전 innerText 파싱 ----
  if (!pp || !out.positive || !out.positive.length) {
    const T = document.body.innerText || '';
    const ratingM = T.match(/([0-5]\.\d{2})\s*\n\s*([\d,]+)/) || T.match(/평점[^0-9]*([0-5]\.\d+)/);
    if (out.rating === undefined || out.rating === null) out.rating = ratingM ? parseFloat(ratingM[1]) : null;
    if (out.reviewCount === undefined || out.reviewCount === null) out.reviewCount = (ratingM && ratingM[2]) ? parseInt(ratingM[2].replace(/,/g, ''), 10) : null;
    function parseBlock(startLabel, endLabels) {
      const lines = T.split('\n').map(s => s.trim()).filter(Boolean);
      const si = lines.indexOf(startLabel); if (si < 0) return [];
      const o = [];
      for (let i = si + 1; i < lines.length; i++) {
        if (endLabels.includes(lines[i])) break;
        const kw = lines[i], num = lines[i + 1];
        if (/^[\d.,]+$/.test(kw)) break;
        if (num && /^[\d,]+$/.test(num)) { o.push({ keyword: kw, count: parseInt(num.replace(/,/g, ''), 10) }); i++; }
        if (o.length >= 20) break;
      }
      return o;
    }
    out.positive = parseBlock('좋아요', ['아쉬워요', '리뷰', '성분']);
    out.negative = parseBlock('아쉬워요', ['좋아요', '리뷰', '성분', '더보기']);
    out.fallback = true;
  }
  return out;
};


(async () => {
  const port = await freePort();
  const profile = fs.mkdtempSync(path.join(os.tmpdir(), 'hh-kit-'));
  const proc = spawn(findChrome(), [`--remote-debugging-port=${port}`, `--user-data-dir=${profile}`,
    '--no-first-run', '--no-default-browser-check', 'about:blank'], { stdio: 'ignore' });
  let browser;
  for (let i = 0; i < 30 && !browser; i++) {
    await sleep(500);
    browser = await puppeteer.connect({ browserURL: `http://127.0.0.1:${port}`, defaultViewport: null }).catch(() => null);
  }
  if (!browser) throw new Error('크롬에 붙지 못했습니다.');
  try {
    const page = (await browser.pages())[0] || await browser.newPage();
    let goodsId = /^\d+$/.test(query.trim()) ? query.trim() : null;
    if (!goodsId) {
      await page.goto('https://www.hwahae.co.kr/search?q=' + encodeURIComponent(query), { waitUntil: 'domcontentloaded', timeout: 60000 });
      await sleep(3500);
      const hit = await page.evaluate(() => {
        const a = [...document.querySelectorAll('a[href^="/goods/"]')].find(x => /\/goods\/\d+/.test(x.getAttribute('href')));
        return a ? { href: a.getAttribute('href'), text: (a.innerText || '').replace(/\s+/g, ' ').trim().slice(0, 80) } : null;
      });
      goodsId = hit ? (hit.href.match(/\/goods\/(\d+)/) || [])[1] : null;
      if (hit) console.log('화해 검색 첫 상품: ' + hit.text);
    }
    if (!goodsId) throw new Error('화해에서 상품을 찾지 못했습니다. 제품명을 짧게 바꿔 보세요.');
    const url = 'https://www.hwahae.co.kr/goods/' + goodsId + '?goods_tab=review_ingredients';
    await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 60000 });
    await sleep(3000);
    const data = await page.evaluate(EXTRACT);
    const out = { source: 'hwahae', query, goodsId, url, collectedAt: new Date().toISOString().slice(0, 10), ...data };
    const file = path.join(process.cwd(), 'hwahae.json');
    fs.writeFileSync(file, JSON.stringify(out, null, 2), 'utf8');
    console.log(`✅ 저장: ${file}`);
    console.log(`제품: ${out.productName} / 별점 ${out.rating} / 리뷰 ${out.reviewCount}건 / 좋아요 키워드 ${(out.positive || []).length}개 / 아쉬워요 키워드 ${(out.negative || []).length}개 / 전성분 ${(out.ingredients || []).length}개`);
  } finally {
    await browser.close().catch(() => {});
    try { proc.kill(); } catch {}
    try { fs.rmSync(profile, { recursive: true, force: true }); } catch {}
  }
})().catch(e => { console.error('❌ ' + e.message); process.exit(1); });
