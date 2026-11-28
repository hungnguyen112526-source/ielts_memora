/* Test nhanh engine làm bài (engine/reader/index.html) trong jsdom, mô phỏng giao thức component của Streamlit.
 *   cd /tmp && npm i jsdom@24 && node <repo>/tests/engine_smoke.js <repo> <fixture.json>
 * fixture.json: {"answers": {"1":"TRUE",...}, "expectedScore": 25, "expectedBand": "6.0"} (điểm kỳ vọng lấy từ core/scoring.py) */
const fs = require('fs'), path = require('path');
const { JSDOM, VirtualConsole } = require(process.env.JSDOM_PATH || 'jsdom');
const repo = path.resolve(process.argv[2] || '.');
const fx = JSON.parse(fs.readFileSync(process.argv[3] || path.join(repo, 'tests/engine_fixture.json'), 'utf8'));
const html = fs.readFileSync(path.join(repo, 'engine/reader/index.html'), 'utf8');
const full = JSON.parse(fs.readFileSync(path.join(repo, 'data/reading/band_4_5/education/test-1.json'), 'utf8'));
const expl = JSON.parse(fs.readFileSync(path.join(repo, 'data/explanations/band-4-5-education-test-1.json'), 'utf8'));

let failed = 0;
const ok = (c, m) => { console.log((c ? '  ✓ ' : '  ✗ ') + m); if (!c) failed++; };
const errors = [], sent = [];
const vc = new VirtualConsole(); vc.on('jsdomError', e => errors.push(String(e.message || e)));
const dom = new JSDOM(html, {
  runScripts: 'dangerously', pretendToBeVisual: true, url: 'http://localhost/', virtualConsole: vc,
  beforeParse(w) { Object.defineProperty(w, 'parent', { value: { postMessage: (m) => sent.push(m) } }); w.scrollTo = () => {}; w.Element.prototype.scrollIntoView = () => {}; },
});
const w = dom.window, $ = (id) => w.document.getElementById(id);
const ev = (code) => w.eval(code);
const render = (args) => w.dispatchEvent(new w.MessageEvent('message', { data: { type: 'streamlit:render', args } }));
const lastEvent = () => { const m = sent.filter(x => x.type === 'streamlit:setComponentValue').pop(); return m && m.value; };
const sleep = (ms) => new Promise(r => setTimeout(r, ms));

const pub = JSON.parse(JSON.stringify(full)); delete pub.answers; delete pub.pairQuestions;
const base = { test: pub, meta: { badge: 'B', seriesTitle: 'Education', uid: 7 }, saved: {}, prefs: {}, scope: 'full',
               theme: 'light', nav: { prev: false, next: true }, sessionKey: 'open1', height: 800 };

(async () => {
  console.log('1. Khởi động');
  ok(w.document.body.classList.contains('booting'), 'trước khi nhận đề: đang ở trạng thái chờ (ẩn khung trống)');
  ok(sent.some(m => m.type === 'streamlit:componentReady'), 'báo componentReady');
  render({ ...base });
  ok(!w.document.body.classList.contains('booting'), 'nhận đề xong: hết trạng thái chờ');
  ok(!$('modalOverlay').classList.contains('hidden') && /Thiết lập/.test($('modalBox').textContent), 'lần đầu mở: hiện hộp thiết lập thời gian');
  ok(ev('TEST.answers') === undefined, 'đề gửi xuống KHÔNG có đáp án khi đang làm');

  console.log('2. Bắt đầu và làm bài');
  ev('startFromSetup()');
  ok(lastEvent() && lastEvent().event === 'autosave' && lastEvent().state.configured === true, 'bắt đầu làm: gửi autosave đã cấu hình');
  for (const [q, v] of Object.entries(fx.answers)) ev(`setAnswer(${q}, ${JSON.stringify(v)}, false)`);
  ev('renderQuestions(TEST.passages[0])');
  ok(ev('countAnswered(0)') > 0, 'ghi nhận đáp án đã chọn');
  ok(ev('stateTs') > 0, 'có mốc ts của lần sửa cuối');
  await sleep(700);
  const bkRaw = w.localStorage.getItem('memora:bk:7:' + full.id + ':full');
  ok(!!bkRaw && JSON.parse(bkRaw).answers['1'] === fx.answers['1'], 'bản nháp được ghi vào localStorage (chống mất bài)');
  ev('(function(){ const a=document.querySelector(\'input.inline-input\'); if(a){a.value=\'a&b <x> "q"\'; } })()');
  ev('setAnswer(99, \'a&b <x> "q"\', false)'); // thử ký tự đặc biệt không làm hỏng HTML
  ev('renderQuestions(TEST.passages[0])');

  console.log('3. Tạm dừng');
  ev('toggleTimer()');
  ok(/Đã tạm dừng/.test($('modalBox').textContent) && !$('modalOverlay').classList.contains('hidden'), 'bấm dừng: bài bị che, hiện hộp tiếp tục');
  ev('toggleTimer()');
  ok($('modalOverlay').classList.contains('hidden'), 'bấm tiếp tục: hộp đóng');

  console.log('4. Nộp bài (đáp án chưa có ở trình duyệt)');
  ev('submitTest(false)');
  let e = lastEvent();
  ok(e.event === 'submit' && e.state.submitted === true, 'gửi sự kiện submit lên server');
  ok(/Đang chấm điểm/.test($('modalBox').textContent), 'hiện "Đang chấm điểm…" (không có đáp án để tự chấm)');
  ok(ev('TEST.answers') === undefined, 'vẫn chưa có đáp án trong trình duyệt');
  ok(errors.length === 0, 'không có lỗi JS: ' + errors.join(' | '));

  console.log('5. Server trả đáp án + lời giải');
  render({ ...base, saved: {}, reveal: { answers: full.answers, pairQuestions: full.pairQuestions || [], explanations: expl } });
  ok(ev('TEST.answers') !== undefined, 'nhận đáp án');
  const modal = $('modalBox').textContent;
  ok(/IELTS Band Score/.test(modal) && modal.includes(fx.expectedBand), `bảng kết quả hiện band ${fx.expectedBand}`);
  ok(ev('appState.tests[0].score') === fx.expectedScore, `điểm engine = điểm server (${fx.expectedScore})`);
  ev('closeModal()');
  ok(w.document.querySelectorAll('details.expl').length > 0, 'có mục "Giải thích đáp án" dưới nhóm câu hỏi');
  ok(!!w.document.querySelector('.expl p') && w.document.querySelector('.expl p').textContent.startsWith('Câu '), 'lời giải gắn đúng số câu');
  ok(w.localStorage.getItem('memora:bk:7:' + full.id + ':full') === null, 'nộp xong: xóa bản nháp');
  ok(errors.length === 0, 'không có lỗi JS: ' + errors.join(' | '));

  console.log('6. Làm lại');
  ev('resetCurrentTest()');
  ok(lastEvent().event === 'reset', 'gửi sự kiện reset');
  ok(ev('TEST.answers') === undefined, 'làm lại: đáp án bị giấu đi');
  render({ ...base, reveal: { answers: full.answers, pairQuestions: [], explanations: expl } });   // render cũ (chưa kịp xử lý reset)
  ok(ev('TEST.answers') === undefined, 'render trễ mang đáp án không làm lộ lại');
  render({ ...base, reveal: null });
  ok(ev('ignoreReveal') === false, 'server xác nhận reset: nhận đáp án bình thường trở lại');

  console.log('7. Khôi phục bản nháp mới hơn bản đã lưu');
  w.localStorage.setItem('memora:bk:7:' + full.id + ':full', JSON.stringify({ answers: { '1': 'TRUE', '2': 'FALSE' }, submitted: false,
    score: null, configured: true, limit: 3600, spent: 120, passage: 0, hl: {}, ts: Date.now() + 5000 }));
  render({ ...base, sessionKey: 'open2', saved: { answers: { '1': 'FALSE' }, configured: true, limit: 3600, spent: 30, passage: 0, hl: {}, ts: 1 } });
  ok(ev('appState.tests[0].answers["2"]') === 'FALSE' && ev('appState.tests[0].spent') === 120, 'dùng bản nháp mới hơn (đáp án + thời gian)');
  ok(ev('dirty') === true, 'đánh dấu để đẩy lên server');

  console.log('8. Bản đã nộp mở lại ("Xem lại")');
  render({ ...base, sessionKey: 'open3', saved: { answers: fx.answers, submitted: true, configured: true, limit: 3600, spent: 900, passage: 0, hl: {}, ts: 5 },
           reveal: { answers: full.answers, pairQuestions: full.pairQuestions || [], explanations: expl } });
  ok(ev('revealed()') && ev('isLocked()'), 'mở lại bài đã nộp: có đáp án, bài bị khóa');
  ok(w.document.querySelectorAll('#questionNavPills button.bg-emerald-500').length > 0, 'ô số câu tô xanh/đỏ theo đúng sai');

  console.log('9. Điện thoại');
  ev("setMobilePane('questions')");
  ok($('passagePane').classList.contains('md:block'), 'khung bài đọc có md:block (không biến mất khi mở rộng cửa sổ)');
  const homeBtn = w.document.querySelector('.lbl-sm').closest('button');
  ok(/Danh sách đề/.test(homeBtn.textContent) && !homeBtn.classList.contains('hidden'), 'nút Danh sách đề luôn hiện (chỉ ẩn chữ trên màn hẹp)');

  console.log(failed ? `\n${failed} kiểm tra THẤT BẠI` : '\nTất cả kiểm tra đạt');
  process.exit(failed ? 1 : 0);
})().catch(e => { console.error(e); process.exit(2); });
