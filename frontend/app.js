const API_URL = 'http://localhost:8080';
let chatHistory = [];
let currentCarousel = null;
let selectedMode = null;

const MODES = {
  guest: { label: 'Guest Mode', icon: '🍹' }
};

function selectMode(mode) {
  selectedMode = mode;

  // Dismiss splash screen
  const splash = document.getElementById('splash');
  if (splash) splash.classList.add('hidden');

  // Show badge in header
  setTimeout(() => {
    const badge = document.getElementById('mode-badge');
    badge.textContent = `${MODES[mode].icon} ${MODES[mode].label} · switch`;
    badge.style.display = 'inline-flex';

    // Welcome message after splash fades
    const welcomeText = "Perfect! I'm here to guide you to your ideal drink. Tell me how you're feeling or what you're craving — I'll take care of the rest. 🍹";

    appendAgentMessage(welcomeText);
  }, 600);
}

function resetMode() {
  selectedMode = null;
  chatHistory = [];

  // Hide badge
  document.getElementById('mode-badge').style.display = 'none';

  // Clear chat
  document.getElementById('chat-container').innerHTML = '';

  // Bring splash back
  const splash = document.getElementById('splash');
  if (splash) splash.classList.remove('hidden');
}

function appendAgentMessage(text) {
  const wrapper = document.createElement('div');
  wrapper.className = 'message agent-message';
  const avatar = document.createElement('div');
  avatar.className = 'avatar';
  avatar.textContent = '🍸';
  const bubble = document.createElement('div');
  bubble.className = 'bubble';
  bubble.innerHTML = `<p>${escapeHtml(text)}</p>`;
  wrapper.appendChild(avatar);
  wrapper.appendChild(bubble);
  chatContainer.appendChild(wrapper);
  scrollToBottom();
}

const chatContainer = document.getElementById('chat-container');
const userInput     = document.getElementById('user-input');

// ── Send on Enter ─────────────────────────────────────────
userInput.addEventListener('keydown', e => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
});

// ── Main send function ────────────────────────────────────
async function sendMessage(overrideText = null) {
  const text = overrideText || userInput.value.trim();
  if (!text) return;

  if (!selectedMode) {
    userInput.placeholder = 'Please select a mode above first ☝️';
    setTimeout(() => userInput.placeholder = "What's your mood tonight?", 2500);
    return;
  }

  userInput.value = '';
  appendUserMessage(text);

  const typing = appendTyping();

  try {
    const res = await fetch(`${API_URL}/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: text, history: chatHistory, mode: selectedMode })
    });

    const data = await res.json();
    typing.remove();

    // Update history
    chatHistory.push({ role: 'user',      content: text });
    chatHistory.push({ role: 'assistant', content: data.message || '' });

    renderAgentResponse(data);

  } catch (err) {
    typing.remove();
    appendErrorMessage();
  }
}

// ── Render agent response ─────────────────────────────────
function renderAgentResponse(data) {
  const wrapper = document.createElement('div');
  wrapper.className = 'message agent-message';

  const avatar = document.createElement('div');
  avatar.className = 'avatar';
  avatar.textContent = '🍸';

  const hasMessage = data.message && data.message.trim().length > 0;
  const hasQuestions = data.clarifying_questions?.length > 0;

  if (hasMessage || hasQuestions) {
    const bubble = document.createElement('div');
    bubble.className = 'bubble';

    if (hasMessage) {
      bubble.innerHTML = `<p>${escapeHtml(data.message)}</p>`;
    }

    // Clarifying questions
    if (hasQuestions) {
      const qDiv = document.createElement('div');
      qDiv.className = 'clarifying-questions';
      qDiv.innerHTML = `<p class="question-text">A couple of quick questions:</p>`;
      data.clarifying_questions.forEach(q => {
        const p = document.createElement('p');
        p.style.cssText = 'font-size:0.88rem;color:#3A8FA3;margin-top:6px;';
        p.textContent = `→ ${q}`;
        qDiv.appendChild(p);
      });
      bubble.appendChild(qDiv);
    }

    wrapper.appendChild(avatar);
    wrapper.appendChild(bubble);
  } else {
    // No message and no questions — still need avatar for layout if there's content below
    // but skip the bubble entirely to avoid empty white box
    wrapper.appendChild(avatar);
  }
  chatContainer.appendChild(wrapper);

  // Shopping list card — appears when agent returns a shopping_list
  if (data.shopping_list) {
    setTimeout(() => {
      const card = buildShoppingList(data.shopping_list);
      chatContainer.appendChild(card);
      scrollToBottom();
    }, 200);
  }

  // Carousel — appears after the bubble if there are recommendations
  if (data.recommendations?.length) {
    setTimeout(() => {
      const carousel = buildCarousel(data.recommendations);
      chatContainer.appendChild(carousel);
      scrollToBottom();
    }, data.shopping_list ? 400 : 200);
  }

  scrollToBottom();
}

// ── Shopping List Card ────────────────────────────────────
function buildShoppingList(list) {
  const cocktailName = list.cocktail || '';
  const categories   = list.categories || [];
  const tip          = list.tip || '';

  const wrapper = document.createElement('div');
  wrapper.className = 'shopping-list-card';
  wrapper.style.animationDelay = '0.1s';

  // Header
  wrapper.innerHTML = `
    <div class="sl-header">
      <div class="sl-title">
        <span class="sl-icon">🛒</span>
        <span>Shopping List — ${escapeHtml(cocktailName)}</span>
      </div>
      <div class="sl-actions">
        <button class="sl-action-btn sl-whatsapp-btn" onclick="shareToWhatsApp(this)">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z"/></svg>
          Send to WhatsApp
        </button>
        <button class="sl-action-btn sl-download-btn" onclick="downloadList(this)">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
          Download
        </button>
        <button class="sl-copy-btn" onclick="copyShoppingList(this)">Copy</button>
      </div>
    </div>
  `;

  // Categories
  categories.forEach(cat => {
    if (!cat.items?.length) return;
    const section = document.createElement('div');
    section.className = 'sl-section';

    const heading = document.createElement('div');
    heading.className = 'sl-section-title';
    heading.innerHTML = `<span>${cat.icon || '•'}</span> ${escapeHtml(cat.name)}`;
    section.appendChild(heading);

    cat.items.forEach(item => {
      const row = document.createElement('div');
      row.className = `sl-item ${item.likely_have ? 'sl-item--have' : ''}`;
      row.innerHTML = `
        <label class="sl-check-label">
          <input type="checkbox" class="sl-checkbox" ${item.likely_have ? 'checked' : ''}/>
          <span class="sl-ingredient">${escapeHtml(item.ingredient)}</span>
          <span class="sl-measure">${escapeHtml(item.measure || '')}</span>
          ${item.likely_have ? '<span class="sl-have-tag">likely have</span>' : ''}
        </label>
        <button class="sl-sub-btn" onclick="askSubstitute('${escapeHtml(item.ingredient)}', '${escapeHtml(cocktailName)}')">🔄 Sub?</button>
      `;
      section.appendChild(row);
    });

    wrapper.appendChild(section);
  });

  // Tip
  if (tip) {
    const tipEl = document.createElement('div');
    tipEl.className = 'sl-tip';
    tipEl.innerHTML = `💡 ${escapeHtml(tip)}`;
    wrapper.appendChild(tipEl);
  }

  return wrapper;
}

function askSubstitute(ingredient, cocktailName) {
  sendMessage(`I can't find ${ingredient} — what can I use instead for the ${cocktailName}?`);
}

function buildListText(card) {
  const title = card.querySelector('.sl-title span:last-child')?.textContent?.trim() || 'Shopping List';
  const lines = [`🛒 ${title}`, ''];
  card.querySelectorAll('.sl-section').forEach(sec => {
    const icon = sec.querySelector('.sl-section-title span')?.textContent?.trim() || '';
    const name = sec.querySelector('.sl-section-title')?.textContent?.replace(icon, '').trim() || '';
    lines.push(`${icon} ${name}`);
    sec.querySelectorAll('.sl-item').forEach(row => {
      const ing     = row.querySelector('.sl-ingredient')?.textContent?.trim();
      const measure = row.querySelector('.sl-measure')?.textContent?.trim();
      if (ing) lines.push(`  • ${measure ? measure + '  ' : ''}${ing}`);
    });
    lines.push('');
  });
  const tip = card.querySelector('.sl-tip')?.textContent?.trim();
  if (tip) lines.push(tip);
  return lines.join('\n').trim();
}

function shareToWhatsApp(btn) {
  const card = btn.closest('.shopping-list-card');
  const text = buildListText(card);
  const url  = `https://wa.me/?text=${encodeURIComponent(text)}`;
  window.open(url, '_blank');
}

function downloadList(btn) {
  const card     = btn.closest('.shopping-list-card');
  const text     = buildListText(card);
  const filename = (card.querySelector('.sl-title span:last-child')?.textContent || 'shopping-list')
                     .replace(/[^a-z0-9]/gi, '-').toLowerCase() + '.txt';
  const blob = new Blob([text], { type: 'text/plain' });
  const a    = document.createElement('a');
  a.href     = URL.createObjectURL(blob);
  a.download = filename;
  a.click();
  URL.revokeObjectURL(a.href);
}

function copyShoppingList(btn) {
  const card = btn.closest('.shopping-list-card');
  const lines = [];
  card.querySelectorAll('.sl-section').forEach(sec => {
    const title = sec.querySelector('.sl-section-title')?.textContent?.trim();
    if (title) lines.push(`\n${title}`);
    sec.querySelectorAll('.sl-item').forEach(row => {
      const ing     = row.querySelector('.sl-ingredient')?.textContent?.trim();
      const measure = row.querySelector('.sl-measure')?.textContent?.trim();
      if (ing) lines.push(`  • ${measure ? measure + ' ' : ''}${ing}`);
    });
  });
  navigator.clipboard.writeText(lines.join('\n').trim()).then(() => {
    btn.textContent = '✓ Copied!';
    setTimeout(() => btn.textContent = 'Copy list', 2000);
  });
}

// ── Build recommendations row ─────────────────────────────
function buildCarousel(recommendations) {
  const wrapper = document.createElement('div');
  wrapper.className = 'recommendations-wrapper';

  const label = document.createElement('p');
  label.className = 'recommendations-label';
  label.textContent = `${recommendations.length} recommendation${recommendations.length > 1 ? 's' : ''} for you`;
  wrapper.appendChild(label);

  const row = document.createElement('div');
  row.className = 'recommendations-row';

  recommendations.forEach((rec, i) => {
    const card = buildCard(rec, i);
    row.appendChild(card);
  });

  wrapper.appendChild(row);
  return wrapper;
}

// ── Build single card ─────────────────────────────────────
function buildCard(rec, index) {
  const card = document.createElement('div');
  card.className = 'cocktail-card';
  card.style.animationDelay = `${index * 0.1}s`;
  card.onclick = () => openModal(rec);

  // Image
  if (rec.thumbnail) {
    const img = document.createElement('img');
    img.className = 'card-img';
    img.src = rec.thumbnail;
    img.alt = rec.name;
    img.onerror = () => img.replaceWith(makePlaceholder('card'));
    card.appendChild(img);
  } else {
    card.appendChild(makePlaceholder('card'));
  }

  const body = document.createElement('div');
  body.className = 'card-body';

  const name = document.createElement('div');
  name.className = 'card-name';
  name.textContent = rec.name;
  body.appendChild(name);

  const badges = document.createElement('div');
  badges.className = 'card-badges';
  if (rec.strength) {
    const b = document.createElement('span');
    b.className = `badge badge-strength-${rec.strength}`;
    b.textContent = rec.strength;
    badges.appendChild(b);
  }
  (rec.flavor_profile || []).slice(0, 2).forEach(f => {
    const b = document.createElement('span');
    b.className = 'badge badge-flavor';
    b.textContent = f;
    badges.appendChild(b);
  });
  body.appendChild(badges);

  if (rec.why) {
    const why = document.createElement('div');
    why.className = 'card-why';
    why.textContent = rec.why.length > 80 ? rec.why.slice(0, 80) + '…' : rec.why;
    body.appendChild(why);
  }

  // Pro guide trigger button — available in both modes
  if (rec.pro_notes) {
    const btn = document.createElement('button');
    btn.className = 'pro-guide-btn';
    btn.innerHTML = `<span>✨</span> How to make it?`;
    btn.onclick = (e) => {
      e.stopPropagation();
      btn.disabled = true;
      btn.style.opacity = '0.5';
      launchProGuide(rec.pro_notes, rec.name);
    };
    body.appendChild(btn);
  }

  card.appendChild(body);
  return card;
}

// ── Pro Preparation Guide ─────────────────────────────────
const PRO_STEPS = [
  { key: 'ratio',      icon: '⚖️', label: 'Ratio',          theme: 'azure'     },
  { key: 'technique',  icon: '🥄', label: 'Technique',      theme: 'sage'      },
  { key: 'garnish',    icon: '🍊', label: 'Garnish',        theme: 'terracotta'},
  { key: 'mistakes',   icon: '⚠️', label: 'Watch Out',      theme: 'gold'      },
  { key: 'variations', icon: '🔄', label: 'Variations',     theme: 'sand'      },
];

function launchProGuide(proNotes, cocktailName) {
  const steps = PRO_STEPS.filter(s => proNotes[s.key]);
  let index = 0;

  // Intro bubble
  const intro = document.createElement('div');
  intro.className = 'message agent-message';
  intro.innerHTML = `
    <div class="avatar">🍸</div>
    <div class="bubble">
      <p>Let's walk through the <strong>${escapeHtml(cocktailName)}</strong> — step by step.</p>
    </div>`;
  chatContainer.appendChild(intro);
  scrollToBottom();

  function revealNextStep() {
    if (index >= steps.length) return;
    const step = steps[index];
    const total = steps.length;

    setTimeout(() => {
      const el = document.createElement('div');
      el.className = `pro-step-bubble theme-${step.theme}`;
      el.innerHTML = `
        <div class="pro-step-header">
          <span class="pro-step-icon">${step.icon}</span>
          <span class="pro-step-label">${step.label}</span>
          <span class="pro-step-counter">${index + 1} / ${total}</span>
        </div>
        <div class="pro-step-content">${escapeHtml(proNotes[step.key])}</div>
        ${index < total - 1
          ? `<button class="pro-step-next" onclick="triggerNextStep(this)">Next →</button>`
          : `<div class="pro-step-done">✦ You're ready to pour.</div>
             <button class="pro-step-followup" onclick="sendFollowUp('${escapeHtml(cocktailName)}')">
               💬 What ingredients do I need?
             </button>`
        }
      `;
      chatContainer.appendChild(el);
      scrollToBottom();
    }, index === 0 ? 600 : 0);

    index++;
  }

  // Expose next trigger to button
  window.triggerNextStep = (btn) => {
    btn.disabled = true;
    btn.style.opacity = '0';
    revealNextStep();
  };

  // Follow-up send — fires a real chat message as if user typed it
  window.sendFollowUp = (name) => {
    const msg = `What ingredients do I need for the ${name}?`;
    sendMessage(msg);
  };

  revealNextStep();
}

// ── Modal ─────────────────────────────────────────────────
function openModal(rec) {
  const modal   = document.getElementById('modal');
  const overlay = document.getElementById('modal-overlay');
  const content = document.getElementById('modal-content');

  const ingredientRows = (rec.ingredients || []).map(i =>
    `<div class="ingredient-row">
       <span>${i.ingredient}</span>
       <span>${i.measure || '—'}</span>
     </div>`
  ).join('');

  const flavorBadges = (rec.flavor_profile || []).map(f =>
    `<span class="badge badge-flavor">${f}</span>`
  ).join('');

  const imgHtml = rec.thumbnail
    ? `<img class="modal-img" src="${rec.thumbnail}" alt="${rec.name}" onerror="this.replaceWith(document.querySelector('.modal-img-placeholder')?.cloneNode(true) || document.createElement('div'))">`
    : `<div class="modal-img-placeholder">🍹</div>`;

  const strengthClass = rec.strength ? `badge-strength-${rec.strength}` : '';

  content.innerHTML = `
    ${imgHtml}
    <div class="modal-body">
      <div class="modal-name">${escapeHtml(rec.name)}</div>
      <div class="modal-badges">
        ${rec.strength ? `<span class="badge ${strengthClass}">${rec.strength}</span>` : ''}
        ${rec.glass ? `<span class="badge badge-flavor">🥃 ${rec.glass}</span>` : ''}
        ${flavorBadges}
      </div>
      ${rec.why ? `<p style="font-style:italic;color:#7A6E62;font-size:0.88rem;margin-bottom:4px;">"${escapeHtml(rec.why)}"</p>` : ''}
      <div class="modal-section-title">Ingredients</div>
      ${ingredientRows}
      ${rec.instructions ? `
        <div class="modal-section-title">How to prepare</div>
        <p class="modal-instructions">${escapeHtml(rec.instructions)}</p>
      ` : ''}
    </div>
  `;

  overlay.classList.add('active');
}

function closeModal(e) {
  if (e.target === document.getElementById('modal-overlay')) closeModalBtn();
}

function closeModalBtn() {
  document.getElementById('modal-overlay').classList.remove('active');
}

document.addEventListener('keydown', e => { if (e.key === 'Escape') closeModalBtn(); });

// ── Helpers ───────────────────────────────────────────────
function appendUserMessage(text) {
  const wrapper = document.createElement('div');
  wrapper.className = 'message user-message';
  const bubble = document.createElement('div');
  bubble.className = 'bubble';
  bubble.textContent = text;
  wrapper.appendChild(bubble);
  chatContainer.appendChild(wrapper);
  scrollToBottom();
}

function appendTyping() {
  const wrapper = document.createElement('div');
  wrapper.className = 'typing-indicator';
  const avatar = document.createElement('div');
  avatar.className = 'avatar';
  avatar.textContent = '🍸';
  const bubble = document.createElement('div');
  bubble.className = 'typing-bubble';
  bubble.innerHTML = `<div class="typing-dot"></div><div class="typing-dot"></div><div class="typing-dot"></div>`;
  wrapper.appendChild(avatar);
  wrapper.appendChild(bubble);
  chatContainer.appendChild(wrapper);
  scrollToBottom();
  return wrapper;
}

function appendErrorMessage() {
  const wrapper = document.createElement('div');
  wrapper.className = 'message agent-message';
  const avatar = document.createElement('div');
  avatar.className = 'avatar';
  avatar.textContent = '🍸';
  const bubble = document.createElement('div');
  bubble.className = 'bubble';
  bubble.innerHTML = `<p style="color:#B84A4A">I'm having a moment at the bar. Give me a second and try again!</p>`;
  wrapper.appendChild(avatar);
  wrapper.appendChild(bubble);
  chatContainer.appendChild(wrapper);
  scrollToBottom();
}

function makePlaceholder(type) {
  const el = document.createElement('div');
  el.className = type === 'card' ? 'card-img-placeholder' : 'modal-img-placeholder';
  el.textContent = '🍹';
  return el;
}

function scrollToBottom() {
  setTimeout(() => {
    window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' });
  }, 50);
}

function escapeHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}
