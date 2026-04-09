"""
Generates a self-contained HTML explorer for the cocktails dataset.
Run: python3 scripts/generate_explorer.py
Then open: data/explorer.html in your browser.
"""

import json
from pathlib import Path

data = json.load(open(Path(__file__).parent.parent / "data" / "cocktails.json"))

# Get unique values for filters
categories = sorted(set(c["category"] for c in data))
alcoholic_types = sorted(set(c["alcoholic"] for c in data))
all_ingredients = sorted(set(
    i["ingredient"] for c in data for i in c["ingredients"]
))

data_json = json.dumps(data)
categories_json = json.dumps(categories)
alcoholic_json = json.dumps(alcoholic_types)

html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>Cocktail DB Explorer</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}

  body {{
    font-family: 'Segoe UI', sans-serif;
    background: linear-gradient(135deg, #0f2027, #203a43, #2c5364);
    min-height: 100vh;
    color: #fff;
  }}

  header {{
    text-align: center;
    padding: 40px 20px 20px;
  }}

  header h1 {{
    font-size: 2.4rem;
    letter-spacing: 2px;
    background: linear-gradient(90deg, #f7971e, #ffd200);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
  }}

  header p {{
    margin-top: 6px;
    color: #aad4e8;
    font-size: 0.95rem;
  }}

  .controls {{
    display: flex;
    flex-wrap: wrap;
    gap: 12px;
    justify-content: center;
    padding: 20px;
    background: rgba(255,255,255,0.05);
    border-bottom: 1px solid rgba(255,255,255,0.1);
  }}

  .controls input, .controls select {{
    padding: 10px 16px;
    border-radius: 30px;
    border: 1px solid rgba(255,255,255,0.2);
    background: rgba(255,255,255,0.08);
    color: #fff;
    font-size: 0.9rem;
    outline: none;
    transition: border 0.2s;
  }}

  .controls input {{ width: 280px; }}
  .controls input::placeholder {{ color: #aaa; }}
  .controls input:focus, .controls select:focus {{
    border-color: #ffd200;
  }}

  .controls select option {{ background: #1a2a3a; color: #fff; }}

  .stats {{
    text-align: center;
    padding: 12px;
    color: #aad4e8;
    font-size: 0.9rem;
  }}

  .grid {{
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
    gap: 20px;
    padding: 24px;
    max-width: 1400px;
    margin: 0 auto;
  }}

  .card {{
    background: rgba(255,255,255,0.07);
    border-radius: 16px;
    overflow: hidden;
    border: 1px solid rgba(255,255,255,0.1);
    cursor: pointer;
    transition: transform 0.2s, box-shadow 0.2s;
  }}

  .card:hover {{
    transform: translateY(-4px);
    box-shadow: 0 12px 30px rgba(0,0,0,0.4);
    border-color: #ffd200;
  }}

  .card img {{
    width: 100%;
    height: 180px;
    object-fit: cover;
    display: block;
  }}

  .card-body {{
    padding: 12px 14px;
  }}

  .card-name {{
    font-size: 0.95rem;
    font-weight: 600;
    margin-bottom: 6px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }}

  .badge {{
    display: inline-block;
    font-size: 0.7rem;
    padding: 2px 8px;
    border-radius: 20px;
    margin-right: 4px;
    margin-bottom: 4px;
  }}

  .badge-category {{ background: rgba(247,151,30,0.25); color: #f7971e; }}
  .badge-alcoholic {{ background: rgba(100,200,120,0.2); color: #7edf8e; }}
  .badge-non {{ background: rgba(100,160,240,0.2); color: #80b4f0; }}

  .card-ingredients {{
    margin-top: 8px;
    font-size: 0.75rem;
    color: #aac4d8;
    line-height: 1.5;
  }}

  /* Modal */
  .modal-overlay {{
    display: none;
    position: fixed;
    inset: 0;
    background: rgba(0,0,0,0.75);
    z-index: 100;
    justify-content: center;
    align-items: center;
    padding: 20px;
  }}

  .modal-overlay.active {{ display: flex; }}

  .modal {{
    background: linear-gradient(145deg, #1a2a3a, #0d1f2d);
    border-radius: 20px;
    border: 1px solid rgba(255,215,0,0.3);
    max-width: 600px;
    width: 100%;
    max-height: 85vh;
    overflow-y: auto;
    padding: 0;
  }}

  .modal img {{
    width: 100%;
    height: 240px;
    object-fit: cover;
    border-radius: 20px 20px 0 0;
    display: block;
  }}

  .modal-content {{ padding: 24px; }}

  .modal-title {{
    font-size: 1.6rem;
    font-weight: 700;
    background: linear-gradient(90deg, #f7971e, #ffd200);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin-bottom: 12px;
  }}

  .modal-meta {{
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    margin-bottom: 16px;
  }}

  .modal-section-title {{
    font-size: 0.8rem;
    text-transform: uppercase;
    letter-spacing: 1px;
    color: #ffd200;
    margin-bottom: 8px;
    margin-top: 16px;
  }}

  .ingredient-list {{ list-style: none; }}

  .ingredient-list li {{
    display: flex;
    justify-content: space-between;
    padding: 5px 0;
    border-bottom: 1px solid rgba(255,255,255,0.06);
    font-size: 0.88rem;
  }}

  .ingredient-list li span:last-child {{ color: #aad4e8; }}

  .instructions {{
    font-size: 0.88rem;
    line-height: 1.7;
    color: #c8dde8;
  }}

  .modal-close {{
    position: absolute;
    top: 16px;
    right: 20px;
    background: rgba(0,0,0,0.5);
    border: none;
    color: #fff;
    font-size: 1.4rem;
    cursor: pointer;
    border-radius: 50%;
    width: 36px;
    height: 36px;
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 10;
  }}

  .modal-wrapper {{ position: relative; }}

  ::-webkit-scrollbar {{ width: 6px; }}
  ::-webkit-scrollbar-track {{ background: transparent; }}
  ::-webkit-scrollbar-thumb {{ background: rgba(255,210,0,0.3); border-radius: 3px; }}

  .no-results {{
    text-align: center;
    padding: 60px 20px;
    color: #aaa;
    font-size: 1rem;
    grid-column: 1 / -1;
  }}
</style>
</head>
<body>

<header>
  <h1>Cocktail DB Explorer</h1>
  <p>426 cocktails · TheCocktailDB · AI Mixologist project data</p>
</header>

<div class="controls">
  <input type="text" id="search" placeholder="Search by name or ingredient..."/>
  <select id="filter-category">
    <option value="">All categories</option>
  </select>
  <select id="filter-alcoholic">
    <option value="">All types</option>
  </select>
  <select id="sort-by">
    <option value="name">Sort: Name A–Z</option>
    <option value="ingredients">Sort: Most ingredients</option>
    <option value="category">Sort: Category</option>
  </select>
</div>

<div class="stats" id="stats">Showing 426 cocktails</div>

<div class="grid" id="grid"></div>

<div class="modal-overlay" id="modal-overlay" onclick="closeModal(event)">
  <div class="modal-wrapper">
    <button class="modal-close" onclick="closeModalBtn()">✕</button>
    <div class="modal" id="modal"></div>
  </div>
</div>

<script>
const DATA = {data_json};
const CATEGORIES = {categories_json};
const ALCOHOLIC = {alcoholic_json};

// Populate filter dropdowns
const catSelect = document.getElementById('filter-category');
CATEGORIES.forEach(c => {{
  const opt = document.createElement('option');
  opt.value = c; opt.textContent = c;
  catSelect.appendChild(opt);
}});

const alcSelect = document.getElementById('filter-alcoholic');
ALCOHOLIC.forEach(a => {{
  const opt = document.createElement('option');
  opt.value = a; opt.textContent = a;
  alcSelect.appendChild(opt);
}});

function getFiltered() {{
  const q = document.getElementById('search').value.toLowerCase();
  const cat = document.getElementById('filter-category').value;
  const alc = document.getElementById('filter-alcoholic').value;
  const sort = document.getElementById('sort-by').value;

  let results = DATA.filter(c => {{
    const matchName = c.name.toLowerCase().includes(q);
    const matchIng = c.ingredients.some(i => i.ingredient.toLowerCase().includes(q));
    const matchSearch = !q || matchName || matchIng;
    const matchCat = !cat || c.category === cat;
    const matchAlc = !alc || c.alcoholic === alc;
    return matchSearch && matchCat && matchAlc;
  }});

  results.sort((a, b) => {{
    if (sort === 'name') return a.name.localeCompare(b.name);
    if (sort === 'ingredients') return b.ingredients.length - a.ingredients.length;
    if (sort === 'category') return a.category.localeCompare(b.category);
    return 0;
  }});

  return results;
}}

function render() {{
  const results = getFiltered();
  const grid = document.getElementById('grid');
  document.getElementById('stats').textContent = `Showing ${{results.length}} cocktails`;

  if (results.length === 0) {{
    grid.innerHTML = '<div class="no-results">No cocktails match your search.</div>';
    return;
  }}

  grid.innerHTML = results.map((c, idx) => {{
    const isAlc = c.alcoholic === 'Alcoholic';
    const ingPreview = c.ingredients.slice(0, 3).map(i => i.ingredient).join(', ');
    const more = c.ingredients.length > 3 ? ` +${{c.ingredients.length - 3}} more` : '';
    return `
      <div class="card" onclick="openModal('${{c.id}}')">
        <img src="${{c.thumbnail}}/preview" alt="${{c.name}}" loading="lazy" onerror="this.src='${{c.thumbnail}}'"/>
        <div class="card-body">
          <div class="card-name">${{c.name}}</div>
          <span class="badge badge-category">${{c.category}}</span>
          <span class="badge ${{isAlc ? 'badge-alcoholic' : 'badge-non'}}">${{c.alcoholic}}</span>
          <div class="card-ingredients">${{ingPreview}}${{more}}</div>
        </div>
      </div>
    `;
  }}).join('');
}}

function openModal(id) {{
  const c = DATA.find(x => x.id === id);
  if (!c) return;
  const modal = document.getElementById('modal');
  const ingList = c.ingredients.map(i =>
    `<li><span>${{i.ingredient}}</span><span>${{i.measure || '—'}}</span></li>`
  ).join('');
  const tags = c.tags.length ? `<span class="badge badge-category">${{c.tags.join(', ')}}</span>` : '';
  modal.innerHTML = `
    <img src="${{c.thumbnail}}" alt="${{c.name}}"/>
    <div class="modal-content">
      <div class="modal-title">${{c.name}}</div>
      <div class="modal-meta">
        <span class="badge badge-category">${{c.category}}</span>
        <span class="badge badge-${{c.alcoholic === 'Alcoholic' ? 'alcoholic' : 'non'}}">${{c.alcoholic}}</span>
        <span class="badge badge-non">🥃 ${{c.glass}}</span>
        ${{tags}}
      </div>
      <div class="modal-section-title">Ingredients (${{c.ingredients.length}})</div>
      <ul class="ingredient-list">${{ingList}}</ul>
      <div class="modal-section-title">Instructions</div>
      <p class="instructions">${{c.instructions}}</p>
    </div>
  `;
  document.getElementById('modal-overlay').classList.add('active');
}}

function closeModal(e) {{
  if (e.target === document.getElementById('modal-overlay')) closeModalBtn();
}}

function closeModalBtn() {{
  document.getElementById('modal-overlay').classList.remove('active');
}}

document.addEventListener('keydown', e => {{ if (e.key === 'Escape') closeModalBtn(); }});

['search', 'filter-category', 'filter-alcoholic', 'sort-by'].forEach(id => {{
  document.getElementById(id).addEventListener('input', render);
}});

render();
</script>
</body>
</html>
"""

out = Path(__file__).parent.parent / "data" / "explorer.html"
out.write_text(html)
print(f"Explorer saved to {out}")
