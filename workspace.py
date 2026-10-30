"""Localized multi-mode AI workspace for Prey Open AGI."""
import logging
from flask import request, render_template_string
from analiz import LANGUAGES, ai_analizi, webde_ara

log = logging.getLogger(__name__)
MODES = {
 "research": "Act as a rigorous research analyst. Separate verified facts, assumptions and unknowns. Never invent sources or facts.",
 "web3": "Act as a Web3 protocol analyst. Assess product status, architecture, token utility, supply, unlocks, integrations, security and risks. Never invent metrics, prices, listings or partnerships. No investment advice.",
 "coding": "Act as a senior software engineer. Diagnose the problem, preserve existing behavior, propose safe maintainable code, and include tests and security considerations."
}
T = {
 "tr": ["AI Çalışma Alanı","← Prey Open AGI ana sayfası","Tek çalışma alanı. Üç odaklı mod.","Çalışma modu","AI Araştırma","Web3 İstihbaratı","AI Kodlama","Görevini açıkla","Ne araştırmak, analiz etmek veya geliştirmek istiyorsun?","Yanıt dili","Ücretsiz web aramasını etkinleştir (kredi tasarrufu için varsayılan olarak kapalı)","Çalıştır","Sonuç","Lütfen 12.000 karakterden kısa bir görev gir.","İstek başarısız. Fortytwo API anahtarını ve Render kayıtlarını kontrol et"],
 "en": ["AI Workspace","← Prey Open AGI home","One workspace. Three focused modes.","Workspace mode","AI Research","Web3 Intelligence","AI Coding","Describe your task","What would you like to research, analyze, or build?","Response language","Enable free web search (off by default to save credits)","Run","Result","Please enter a task under 12,000 characters.","Request failed. Check the Fortytwo API key and Render logs"],
 "es": ["Espacio de trabajo de IA","← Inicio de Prey Open AGI","Un espacio de trabajo. Tres modos especializados.","Modo de trabajo","Investigación con IA","Inteligencia Web3","Programación con IA","Describe tu tarea","¿Qué quieres investigar, analizar o desarrollar?","Idioma de respuesta","Activar búsqueda web gratuita (desactivada por defecto para ahorrar créditos)","Ejecutar","Resultado","Introduce una tarea de menos de 12.000 caracteres.","La solicitud falló. Comprueba la clave API de Fortytwo y los registros de Render"],
 "pt": ["Espaço de trabalho de IA","← Início do Prey Open AGI","Um espaço de trabalho. Três modos especializados.","Modo de trabalho","Pesquisa com IA","Inteligência Web3","Programação com IA","Descreva sua tarefa","O que você deseja pesquisar, analisar ou desenvolver?","Idioma da resposta","Ativar pesquisa gratuita na web (desativada por padrão para economizar créditos)","Executar","Resultado","Digite uma tarefa com menos de 12.000 caracteres.","A solicitação falhou. Verifique a chave da API Fortytwo e os logs do Render"],
 "zh": ["AI 工作区","← 返回 Prey Open AGI 首页","一个工作区，三种专注模式。","工作模式","AI 研究","Web3 情报","AI 编程","描述你的任务","你想研究、分析或构建什么？","回复语言","启用免费网页搜索（默认关闭以节省额度）","运行","结果","请输入少于 12,000 个字符的任务。","请求失败。请检查 Fortytwo API 密钥和 Render 日志"],
 "ru": ["Рабочее пространство ИИ","← Главная Prey Open AGI","Одно пространство. Три специализированных режима.","Режим работы","Исследование ИИ","Аналитика Web3","Программирование с ИИ","Опишите задачу","Что вы хотите исследовать, проанализировать или разработать?","Язык ответа","Включить бесплатный веб-поиск (по умолчанию выключен для экономии кредитов)","Запустить","Результат","Введите задачу длиной менее 12 000 символов.","Запрос не выполнен. Проверьте API-ключ Fortytwo и журналы Render"]
}
PAGE = """<!doctype html><html lang="{{lang}}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{{t[0]}} · Prey Open AGI</title><style>body{margin:0;background:#08131d;color:#edf1ff;font:15px/1.6 system-ui}.wrap{max-width:900px;margin:auto;padding:30px 18px}.panel{background:#102330;border:1px solid #254252;border-radius:18px;padding:22px;margin:18px 0}a{color:#39d6c4}label{display:block;margin:12px 0 6px;color:#a0abc5}select,textarea{width:100%;box-sizing:border-box;padding:13px;border-radius:10px;border:1px solid #254252;background:#0b1a25;color:#edf1ff;font:inherit}textarea{min-height:170px}button{width:100%;padding:14px;border:0;border-radius:10px;margin-top:14px;background:linear-gradient(100deg,#39d6c4,#65aaff);font-weight:800;cursor:pointer}.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}.mode{border:1px solid #254252;border-radius:12px;padding:12px}.result{overflow-wrap:anywhere}.result a{color:#39d6c4}@media(max-width:650px){.grid{grid-template-columns:1fr}}</style></head><body><main class="wrap"><a href="/">{{t[1]}}</a><h1>{{t[0]}}</h1><p>{{t[2]}}</p><section class="panel"><form method="post"><label>{{t[3]}}</label><div class="grid"><label class="mode"><input type="radio" name="mode" value="research" {% if mode=="research" %}checked{% endif %}> {{t[4]}}</label><label class="mode"><input type="radio" name="mode" value="web3" {% if mode=="web3" %}checked{% endif %}> {{t[5]}}</label><label class="mode"><input type="radio" name="mode" value="coding" {% if mode=="coding" %}checked{% endif %}> {{t[6]}}</label></div><label for="task">{{t[7]}}</label><textarea id="task" name="task" maxlength="12000" placeholder="{{t[8]}}" required>{{task}}</textarea><label for="lang">{{t[9]}}</label><select id="lang" name="lang">{% for c,n in languages.items() %}<option value="{{c}}" {% if c==lang %}selected{% endif %}>{{n}}</option>{% endfor %}</select><label><input type="checkbox" name="search" value="yes" {% if use_search %}checked{% endif %}> {{t[10]}}</label><button type="submit">{{t[11]}}</button></form></section>{% if error %}<section class="panel">{{error}}</section>{% endif %}{% if report %}<section class="panel"><h2>{{t[12]}}</h2><div class="result">{{report}}</div></section>{% endif %}</main></body></html>"""
def register_workspace(app, render_report):
 @app.route("/workspace", methods=["GET", "POST"])
 def workspace():
  mode = request.form.get("mode", "research")
  if mode not in MODES: mode = "research"
  lang = request.form.get("lang", "tr")
  if lang not in LANGUAGES: lang = "tr"
  t = T.get(lang, T["tr"])
  task = request.form.get("task", "").strip()
  use_search = request.form.get("search") == "yes"
  report = error = None
  if request.method == "POST":
   if not task or len(task) > 12000: error = t[13]
   else:
    try:
     sources = webde_ara(task, max_sonuc=3) if use_search else []
     context = {"mode": mode, "instructions": MODES[mode], "task": task}
     answer = ai_analizi(task, proje_verisi=context, arama_sonuclari=sources or [], dil=lang)
     report = render_report(answer)
    except Exception:
     log.exception("AI workspace failed")
     error = t[14]
  return render_template_string(PAGE, mode=mode, lang=lang, languages=LANGUAGES, t=t, task=task, use_search=use_search, report=report, error=error)