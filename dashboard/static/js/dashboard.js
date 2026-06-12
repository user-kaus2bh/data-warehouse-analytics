/* dashboard.js — All chart rendering for the analytics dashboard */

// ── Plotly theme ───────────────────────────────────────────────────────────
const BG    = '#161b27';
const PAPER = '#161b27';
const GRID  = '#2a3350';
const TEXT  = '#94a3b8';
const FONT  = { family: 'Inter, sans-serif', color: TEXT, size: 11 };

const COLORS = {
  blue:   '#3b82f6',
  cyan:   '#06b6d4',
  green:  '#10b981',
  orange: '#f59e0b',
  purple: '#8b5cf6',
  red:    '#ef4444',
  pink:   '#ec4899',
  teal:   '#14b8a6',
};

const PALETTE = Object.values(COLORS);

const CAT_COLORS = {
  Electronics: COLORS.blue,
  Software:    COLORS.cyan,
  Furniture:   COLORS.orange,
  Accessories: COLORS.green,
  Stationery:  COLORS.purple,
};

const CHAN_COLORS = {
  Online:     COLORS.blue,
  Partner:    COLORS.cyan,
  Direct:     COLORS.green,
  'Sales Rep':COLORS.orange,
};

const SEG_COLORS = {
  Enterprise: COLORS.blue,
  Smb:        COLORS.cyan,
  SMB:        COLORS.cyan,
  Startup:    COLORS.green,
  Consumer:   COLORS.orange,
};

const LTV_COLORS = {
  Platinum: '#e5e7eb',
  Gold:     '#f59e0b',
  Silver:   '#94a3b8',
  Bronze:   '#c2814a',
};

const REGION_COLORS = ['#3b82f6','#06b6d4','#10b981','#f59e0b'];

function baseLayout(extra = {}) {
  return {
    paper_bgcolor: PAPER,
    plot_bgcolor:  BG,
    font:          FONT,
    margin:        { t: 20, r: 20, b: 40, l: 60 },
    xaxis:  { gridcolor: GRID, zerolinecolor: GRID, tickfont: FONT },
    yaxis:  { gridcolor: GRID, zerolinecolor: GRID, tickfont: FONT },
    legend: { bgcolor: 'transparent', font: FONT },
    hoverlabel: { bgcolor: '#1e2535', font: { family: 'Inter', size: 12 }, bordercolor: GRID },
    ...extra
  };
}

const CONFIG = { displayModeBar: false, responsive: true };

function fmt(n) {
  if (n >= 1e7) return '₹' + (n / 1e7).toFixed(1) + ' Cr';
  if (n >= 1e5) return '₹' + (n / 1e5).toFixed(1) + 'L';
  return '₹' + n.toLocaleString('en-IN');
}
function fmtShort(n) {
  if (n >= 1e7) return (n / 1e7).toFixed(1) + 'Cr';
  if (n >= 1e5) return (n / 1e5).toFixed(1) + 'L';
  return n.toLocaleString('en-IN');
}

// ── Navigation ─────────────────────────────────────────────────────────────
const SECTION_TITLES = {
  overview:   'Overview',
  trends:     'Revenue Trends',
  breakdown:  'Region & Segment',
  channels:   'Sales Channels',
  products:   'Top Products',
  categories: 'Category Analysis',
  ltv:        'Customer Lifetime Value',
  cohort:     'Cohort Analysis',
  campaigns:  'Campaigns & ROI',
};

const loaded = new Set();

document.querySelectorAll('.nav-item').forEach(link => {
  link.addEventListener('click', e => {
    e.preventDefault();
    const sec = link.dataset.section;
    document.querySelectorAll('.nav-item').forEach(l => l.classList.remove('active'));
    link.classList.add('active');
    document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
    document.getElementById('section-' + sec).classList.add('active');
    document.getElementById('section-title').textContent = SECTION_TITLES[sec];
    if (!loaded.has(sec)) { loadSection(sec); loaded.add(sec); }
  });
});

function loadSection(sec) {
  switch (sec) {
    case 'trends':     loadTrends();     break;
    case 'breakdown':  loadBreakdown();  break;
    case 'channels':   loadChannels();   break;
    case 'products':   loadProducts();   break;
    case 'categories': loadCategories(); break;
    case 'ltv':        loadLTV();        break;
    case 'cohort':     loadCohort();     break;
    case 'campaigns':  loadCampaigns();  break;
  }
}

// ── On load: Overview ──────────────────────────────────────────────────────
window.addEventListener('load', () => {
  loadKPIs();
  loadOverview();
  loaded.add('overview');
});

// ── KPI Cards ──────────────────────────────────────────────────────────────
async function loadKPIs() {
  const d = await fetch('/api/kpis').then(r => r.json());
  document.getElementById('val-revenue').textContent  = fmt(d.total_revenue);
  document.getElementById('sub-revenue').textContent  = `Profit: ${fmt(d.total_profit)}`;
  document.getElementById('val-profit').textContent   = d.avg_margin + '%';
  document.getElementById('sub-profit').textContent   = `Avg margin across all sales`;
  document.getElementById('val-orders').textContent   = d.total_orders.toLocaleString();
  document.getElementById('sub-orders').textContent   = `AOV: ${fmt(d.avg_order_value)}`;
  document.getElementById('val-customers').textContent = d.unique_customers.toLocaleString();
  document.getElementById('sub-customers').textContent = `YoY growth: +${d.yoy_growth}%`;
  document.querySelectorAll('.kpi-card').forEach(c => c.classList.remove('loading'));
}

// ── Overview ───────────────────────────────────────────────────────────────
async function loadOverview() {
  const [monthly, cats, regions, ltv] = await Promise.all([
    fetch('/api/revenue/monthly').then(r => r.json()),
    fetch('/api/products/category').then(r => r.json()),
    fetch('/api/revenue/region').then(r => r.json()),
    fetch('/api/customers/ltv').then(r => r.json()),
  ]);

  // Trend line
  Plotly.newPlot('chart-overview-trend', [{
    x: monthly.map(r => r.year_month),
    y: monthly.map(r => r.revenue),
    type: 'scatter', mode: 'lines+markers',
    line: { color: COLORS.blue, width: 2 },
    marker: { size: 4, color: COLORS.blue },
    fill: 'tozeroy', fillcolor: 'rgba(59,130,246,0.08)',
    name: 'Revenue',
    hovertemplate: '%{x}<br>Revenue: ₹%{y:,.0f}<extra></extra>',
  }], baseLayout({ margin: { t:20,r:20,b:50,l:80 } }), CONFIG);

  // Category donut
  Plotly.newPlot('chart-overview-category', [{
    labels: cats.map(r => r.category),
    values: cats.map(r => r.revenue),
    type: 'pie', hole: 0.55,
    marker: { colors: cats.map(r => CAT_COLORS[r.category] || COLORS.blue) },
    textinfo: 'label+percent',
    textfont: { color: TEXT, size: 11 },
    hovertemplate: '%{label}<br>%{value:,.0f}<br>%{percent}<extra></extra>',
  }], baseLayout({ margin:{t:20,r:20,b:20,l:20}, showlegend:false }), CONFIG);

  // Region bar
  Plotly.newPlot('chart-overview-region', [{
    x: regions.map(r => r.region),
    y: regions.map(r => r.revenue),
    type: 'bar',
    marker: { color: REGION_COLORS, borderRadius: 6 },
    hovertemplate: '%{x}<br>₹%{y:,.0f}<extra></extra>',
  }], baseLayout({ margin:{t:20,r:20,b:40,l:80}, showlegend:false }), CONFIG);

  // LTV donut
  const tiers = ltv.tiers;
  Plotly.newPlot('chart-overview-ltv', [{
    labels: tiers.map(t => t.ltv_tier),
    values: tiers.map(t => t.revenue),
    type: 'pie', hole: 0.55,
    marker: { colors: tiers.map(t => LTV_COLORS[t.ltv_tier] || COLORS.blue) },
    textinfo: 'label+percent',
    textfont: { color: TEXT, size: 11 },
    hovertemplate: '%{label}<br>%{value:,.0f}<br>%{percent}<extra></extra>',
  }], baseLayout({ margin:{t:20,r:20,b:20,l:20}, showlegend:false }), CONFIG);
}

// ── Trends ─────────────────────────────────────────────────────────────────
async function loadTrends() {
  const [monthly, yoy] = await Promise.all([
    fetch('/api/revenue/monthly').then(r => r.json()),
    fetch('/api/revenue/yoy').then(r => r.json()),
  ]);

  // Monthly revenue + profit
  Plotly.newPlot('chart-monthly', [
    {
      x: monthly.map(r => r.year_month),
      y: monthly.map(r => r.revenue),
      name: 'Revenue', type: 'scatter', mode: 'lines',
      line: { color: COLORS.blue, width: 2.5 },
      fill: 'tozeroy', fillcolor: 'rgba(59,130,246,0.1)',
      hovertemplate: '%{x}<br>Revenue: ₹%{y:,.0f}<extra></extra>',
    },
    {
      x: monthly.map(r => r.year_month),
      y: monthly.map(r => r.profit),
      name: 'Profit', type: 'scatter', mode: 'lines',
      line: { color: COLORS.green, width: 2 },
      fill: 'tozeroy', fillcolor: 'rgba(16,185,129,0.08)',
      hovertemplate: '%{x}<br>Profit: ₹%{y:,.0f}<extra></extra>',
    },
    {
      x: monthly.map(r => r.year_month),
      y: monthly.map(r => r.total_orders),
      name: 'Orders', type: 'bar',
      yaxis: 'y2',
      marker: { color: 'rgba(139,92,246,0.3)', borderRadius: 3 },
      hovertemplate: '%{x}<br>Orders: %{y}<extra></extra>',
    },
  ], baseLayout({
    margin: { t:20,r:80,b:60,l:80 },
    yaxis2: { title:'Orders', overlaying:'y', side:'right', gridcolor:GRID, showgrid:false },
    legend: { orientation:'h', y:-0.15 },
  }), CONFIG);

  // YoY grouped bar
  Plotly.newPlot('chart-yoy', [
    { x: yoy.map(r=>r.month_name), y: yoy.map(r=>r.revenue_2022), name:'2022', type:'bar',
      marker:{color:COLORS.purple, borderRadius:4}, hovertemplate:'%{x} 2022<br>₹%{y:,.0f}<extra></extra>' },
    { x: yoy.map(r=>r.month_name), y: yoy.map(r=>r.revenue_2023), name:'2023', type:'bar',
      marker:{color:COLORS.cyan, borderRadius:4}, hovertemplate:'%{x} 2023<br>₹%{y:,.0f}<extra></extra>' },
    { x: yoy.map(r=>r.month_name), y: yoy.map(r=>r.revenue_2024), name:'2024', type:'bar',
      marker:{color:COLORS.blue, borderRadius:4}, hovertemplate:'%{x} 2024<br>₹%{y:,.0f}<extra></extra>' },
  ], baseLayout({
    barmode: 'group',
    margin: { t:20,r:20,b:60,l:80 },
    legend: { orientation:'h', y:-0.2 },
  }), CONFIG);
}

// ── Breakdown ──────────────────────────────────────────────────────────────
async function loadBreakdown() {
  const [regions, segments] = await Promise.all([
    fetch('/api/revenue/region').then(r => r.json()),
    fetch('/api/revenue/segment').then(r => r.json()),
  ]);

  // Region horizontal bar
  Plotly.newPlot('chart-region', [{
    y: regions.map(r => r.region),
    x: regions.map(r => r.revenue),
    type: 'bar', orientation: 'h',
    marker: { color: REGION_COLORS, borderRadius: 6 },
    hovertemplate: '%{y}<br>Revenue: ₹%{x:,.0f}<extra></extra>',
    text: regions.map(r => fmtShort(r.revenue)),
    textposition: 'outside', textfont: { color: TEXT },
  }], baseLayout({ margin:{t:20,r:80,b:40,l:80}, showlegend:false }), CONFIG);

  // Segment donut
  Plotly.newPlot('chart-segment', [{
    labels: segments.map(r => r.segment),
    values: segments.map(r => r.revenue),
    type: 'pie', hole: 0.55,
    marker: { colors: segments.map(r => SEG_COLORS[r.segment] || COLORS.blue) },
    textinfo: 'label+percent',
    textfont: { color: TEXT, size: 11 },
    hovertemplate: '%{label}<br>Revenue: ₹%{value:,.0f}<br>%{percent}<extra></extra>',
  }], baseLayout({ margin:{t:20,r:20,b:20,l:20}, showlegend:false }), CONFIG);

  // Region detail: grouped bar revenue + profit
  Plotly.newPlot('chart-region-detail', [
    { x: regions.map(r=>r.region), y: regions.map(r=>r.revenue), name:'Revenue',
      type:'bar', marker:{color:COLORS.blue, borderRadius:6},
      hovertemplate:'%{x}<br>Revenue: ₹%{y:,.0f}<extra></extra>' },
    { x: regions.map(r=>r.region), y: regions.map(r=>r.profit), name:'Profit',
      type:'bar', marker:{color:COLORS.green, borderRadius:6},
      hovertemplate:'%{x}<br>Profit: ₹%{y:,.0f}<extra></extra>' },
  ], baseLayout({ barmode:'group', margin:{t:20,r:20,b:40,l:80} }), CONFIG);
}

// ── Channels ───────────────────────────────────────────────────────────────
async function loadChannels() {
  const data = await fetch('/api/revenue/channel').then(r => r.json());

  Plotly.newPlot('chart-channel-bar', [{
    x: data.map(r => r.channel),
    y: data.map(r => r.revenue),
    type: 'bar',
    marker: { color: data.map(r => CHAN_COLORS[r.channel] || COLORS.blue), borderRadius: 6 },
    hovertemplate: '%{x}<br>₹%{y:,.0f}<extra></extra>',
    text: data.map(r => fmtShort(r.revenue)),
    textposition: 'outside', textfont: { color: TEXT },
  }], baseLayout({ margin:{t:20,r:20,b:40,l:80}, showlegend:false }), CONFIG);

  Plotly.newPlot('chart-channel-pie', [{
    labels: data.map(r => r.channel),
    values: data.map(r => r.revenue),
    type: 'pie', hole: 0.55,
    marker: { colors: data.map(r => CHAN_COLORS[r.channel] || COLORS.blue) },
    textinfo: 'label+percent',
    textfont: { color: TEXT, size: 11 },
    hovertemplate: '%{label}<br>₹%{value:,.0f}<br>%{percent}<extra></extra>',
  }], baseLayout({ margin:{t:20,r:20,b:20,l:20}, showlegend:false }), CONFIG);

  // Detail: revenue + profit + AOV
  Plotly.newPlot('chart-channel-detail', [
    { x: data.map(r=>r.channel), y: data.map(r=>r.revenue), name:'Revenue',
      type:'bar', marker:{color:COLORS.blue,borderRadius:6} },
    { x: data.map(r=>r.channel), y: data.map(r=>r.profit), name:'Profit',
      type:'bar', marker:{color:COLORS.green,borderRadius:6} },
    { x: data.map(r=>r.channel), y: data.map(r=>r.avg_margin), name:'Margin %',
      type:'scatter', mode:'markers+lines', yaxis:'y2',
      marker:{color:COLORS.orange,size:10}, line:{color:COLORS.orange,width:2} },
  ], baseLayout({
    barmode: 'group',
    margin: { t:20,r:80,b:40,l:80 },
    yaxis2: { title:'Margin %', overlaying:'y', side:'right', gridcolor:GRID, showgrid:false },
  }), CONFIG);
}

// ── Products ───────────────────────────────────────────────────────────────
async function loadProducts() {
  const data = await fetch('/api/products/top').then(r => r.json());

  // Horizontal bar — revenue
  Plotly.newPlot('chart-products-bar', [
    { y: data.map(r=>r.product_name), x: data.map(r=>r.revenue),
      name:'Revenue', type:'bar', orientation:'h',
      marker:{color:data.map(r=>CAT_COLORS[r.category]||COLORS.blue), borderRadius:4},
      hovertemplate:'%{y}<br>Revenue: ₹%{x:,.0f}<extra></extra>' },
    { y: data.map(r=>r.product_name), x: data.map(r=>r.profit),
      name:'Profit', type:'bar', orientation:'h',
      marker:{color:'rgba(16,185,129,0.5)', borderRadius:4},
      hovertemplate:'%{y}<br>Profit: ₹%{x:,.0f}<extra></extra>' },
  ], baseLayout({
    barmode:'overlay',
    margin:{t:20,r:80,b:40,l:160},
    yaxis:{autorange:'reversed'},
  }), CONFIG);

  // Scatter: revenue vs margin, bubble = units
  Plotly.newPlot('chart-products-scatter', [{
    x: data.map(r => r.revenue),
    y: data.map(r => r.margin),
    mode: 'markers+text',
    type: 'scatter',
    text: data.map(r => r.product_name.split(' ').slice(0,2).join(' ')),
    textposition: 'top center',
    textfont: { color: TEXT, size: 10 },
    marker: {
      size: data.map(r => Math.max(8, Math.sqrt(r.units || 1) * 1.5)),
      color: data.map(r => CAT_COLORS[r.category] || COLORS.blue),
      opacity: 0.85,
      line: { width: 1, color: '#1e2535' }
    },
    hovertemplate: '<b>%{text}</b><br>Revenue: ₹%{x:,.0f}<br>Margin: %{y:.1f}%<extra></extra>',
  }], baseLayout({
    margin:{t:20,r:20,b:60,l:80},
    xaxis:{ title:'Revenue', gridcolor:GRID },
    yaxis:{ title:'Margin %', gridcolor:GRID },
    showlegend:false,
  }), CONFIG);
}

// ── Categories ─────────────────────────────────────────────────────────────
async function loadCategories() {
  const data = await fetch('/api/products/category').then(r => r.json());

  // Donut
  Plotly.newPlot('chart-cat-donut', [{
    labels: data.map(r => r.category),
    values: data.map(r => r.revenue),
    type: 'pie', hole: 0.6,
    marker: { colors: data.map(r => CAT_COLORS[r.category] || COLORS.blue) },
    textinfo: 'label+percent',
    textfont: { color: TEXT, size: 11 },
    hovertemplate: '%{label}<br>₹%{value:,.0f}<br>%{percent}<extra></extra>',
  }], baseLayout({ margin:{t:20,r:20,b:20,l:20}, showlegend:false }), CONFIG);

  // Margin bar
  Plotly.newPlot('chart-cat-margin', [{
    x: data.map(r => r.category),
    y: data.map(r => r.avg_margin),
    type: 'bar',
    marker: { color: data.map(r => CAT_COLORS[r.category] || COLORS.blue), borderRadius:6 },
    text: data.map(r => r.avg_margin + '%'),
    textposition: 'outside', textfont: { color: TEXT },
    hovertemplate: '%{x}<br>Margin: %{y}%<extra></extra>',
  }], baseLayout({ margin:{t:20,r:20,b:40,l:60}, showlegend:false }), CONFIG);

  // Stacked bar: cost vs profit
  Plotly.newPlot('chart-cat-waterfall', [
    { x: data.map(r=>r.category), y: data.map(r=>r.cost),
      name:'Cost', type:'bar', marker:{color:COLORS.red,borderRadius:0,opacity:0.7} },
    { x: data.map(r=>r.category), y: data.map(r=>r.profit),
      name:'Profit', type:'bar', marker:{color:COLORS.green,borderRadius:0,opacity:0.85} },
  ], baseLayout({
    barmode: 'stack',
    margin:{t:20,r:20,b:40,l:80},
  }), CONFIG);
}

// ── Customer LTV ───────────────────────────────────────────────────────────
async function loadLTV() {
  const data = await fetch('/api/customers/ltv').then(r => r.json());
  const { tiers, top10 } = data;

  // Donut by customers
  Plotly.newPlot('chart-ltv-donut', [{
    labels: tiers.map(t => t.ltv_tier),
    values: tiers.map(t => t.customers),
    type: 'pie', hole: 0.6,
    marker: { colors: tiers.map(t => LTV_COLORS[t.ltv_tier] || COLORS.blue) },
    textinfo: 'label+value',
    textfont: { color: '#1e2535', size: 11 },
    hovertemplate: '%{label}<br>%{value} customers (%{percent})<extra></extra>',
  }], baseLayout({ margin:{t:20,r:20,b:20,l:20}, showlegend:false }), CONFIG);

  // Revenue concentration
  Plotly.newPlot('chart-ltv-revenue', [{
    x: tiers.map(t => t.ltv_tier),
    y: tiers.map(t => t.revenue),
    type: 'bar',
    marker: { color: tiers.map(t => LTV_COLORS[t.ltv_tier] || COLORS.blue), borderRadius:6 },
    text: tiers.map(t => fmtShort(t.revenue)),
    textposition: 'outside', textfont: { color: TEXT },
    hovertemplate: '%{x}<br>₹%{y:,.0f}<extra></extra>',
  }], baseLayout({ margin:{t:20,r:20,b:40,l:80}, showlegend:false }), CONFIG);

  // Top 10 customers horizontal bar
  const rev10 = [...top10].sort((a,b)=>a.revenue-b.revenue);
  Plotly.newPlot('chart-ltv-top', [{
    y: rev10.map(r => r.name),
    x: rev10.map(r => r.revenue),
    type: 'bar', orientation: 'h',
    marker: { color: rev10.map(r => LTV_COLORS[r.ltv_tier] || COLORS.blue), borderRadius:6 },
    hovertemplate: '<b>%{y}</b><br>Revenue: ₹%{x:,.0f}<extra></extra>',
    text: rev10.map(r => fmtShort(r.revenue)),
    textposition: 'outside', textfont: { color: TEXT },
  }], baseLayout({ margin:{t:20,r:80,b:40,l:160}, showlegend:false }), CONFIG);
}

// ── Cohort ─────────────────────────────────────────────────────────────────
async function loadCohort() {
  const rows = await fetch('/api/customers/cohort').then(r => r.json());

  const cohorts   = [...new Set(rows.map(r => r.cohort_month))].sort().slice(0,12);
  const activities= [...new Set(rows.map(r => r.activity_month))].sort().slice(0,24);

  const z = cohorts.map(c =>
    activities.map(a => {
      const found = rows.find(r => r.cohort_month===c && r.activity_month===a);
      return found ? found.revenue : null;
    })
  );

  Plotly.newPlot('chart-cohort', [{
    z, x: activities, y: cohorts,
    type: 'heatmap',
    colorscale: [[0,'#1e2535'],[0.3,'#1d4ed8'],[0.6,'#3b82f6'],[1,'#93c5fd']],
    hovertemplate: 'Cohort: %{y}<br>Month: %{x}<br>Revenue: ₹%{z:,.0f}<extra></extra>',
    showscale: true,
    colorbar: { tickfont: FONT, bgcolor: PAPER, outlinewidth:0 },
  }], baseLayout({
    margin:{t:20,r:80,b:80,l:100},
    xaxis:{ title:'Activity Month', tickangle:-45 },
    yaxis:{ title:'Cohort (First Purchase Month)', autorange:'reversed' },
  }), CONFIG);
}

// ── Campaigns ──────────────────────────────────────────────────────────────
async function loadCampaigns() {
  const data = await fetch('/api/campaigns/roi').then(r => r.json());

  const types = [...new Set(data.map(r => r.campaign_type))];
  const typeColors = {};
  types.forEach((t,i) => typeColors[t] = PALETTE[i % PALETTE.length]);

  // Scatter: budget vs revenue
  const traces = types.map(type => {
    const subset = data.filter(r => r.campaign_type === type);
    return {
      name: type,
      type: 'scatter', mode: 'markers',
      x: subset.map(r => r.budget),
      y: subset.map(r => r.revenue),
      marker: { size: 12, color: typeColors[type], opacity: 0.85,
                line: { width:1, color:'#1e2535' } },
      hovertemplate: '<b>%{text}</b><br>Budget: ₹%{x:,.0f}<br>Revenue: ₹%{y:,.0f}<extra></extra>',
      text: subset.map(r => r.campaign_name),
    };
  });
  Plotly.newPlot('chart-camp-scatter', traces, baseLayout({
    margin:{t:20,r:20,b:60,l:80},
    xaxis:{title:'Budget (₹)'},
    yaxis:{title:'Attributed Revenue (₹)'},
  }), CONFIG);

  // ROI by type bar
  const roiByType = types.map(type => {
    const subset = data.filter(r => r.campaign_type === type);
    return { type, avg_roi: subset.reduce((s,r)=>s+r.roi_pct,0)/subset.length };
  }).sort((a,b)=>b.avg_roi-a.avg_roi);

  Plotly.newPlot('chart-camp-roi', [{
    x: roiByType.map(r => r.type),
    y: roiByType.map(r => parseFloat(r.avg_roi.toFixed(1))),
    type: 'bar',
    marker: { color: roiByType.map(r => typeColors[r.type]), borderRadius:6 },
    text: roiByType.map(r => r.avg_roi.toFixed(0) + '%'),
    textposition: 'outside', textfont:{ color: TEXT },
    hovertemplate: '%{x}<br>Avg ROI: %{y:.1f}%<extra></extra>',
  }], baseLayout({ margin:{t:20,r:20,b:40,l:60}, showlegend:false }), CONFIG);

  // Top campaigns bar
  const sorted = [...data].sort((a,b)=>b.revenue-a.revenue);
  Plotly.newPlot('chart-camp-bar', [
    { y: sorted.map(r=>r.campaign_name), x: sorted.map(r=>r.revenue),
      name:'Revenue', type:'bar', orientation:'h',
      marker:{color:sorted.map(r=>typeColors[r.campaign_type]||COLORS.blue), borderRadius:4},
      hovertemplate:'<b>%{y}</b><br>Revenue: ₹%{x:,.0f}<extra></extra>' },
  ], baseLayout({
    margin:{t:20,r:80,b:40,l:220},
    yaxis:{autorange:'reversed'},
    showlegend:false,
  }), CONFIG);
}
