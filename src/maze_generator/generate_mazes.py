#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = [
#     "reportlab>=4.0",
# ]
# ///
"""
generate_mazes.py
=================
Generate an A4 black-and-white PDF with a configurable number of mazes whose
difficulty increases page by page. The mazes are intended for children aged
4-6 and are decorated with fantasy line-art (unicorns, cats, bunnies,
butterflies, castles, rainbows, ...).

Every run produces DIFFERENT mazes. Randomness covers:
  * the internal paths (recursive-backtracker carving, seeded from system entropy)
  * the theme/illustration assigned to each page

Each maze is "perfect": it is a spanning tree, so exactly one solution exists.
That single solution is also guaranteed to be LONG: the entrance and exit are
placed at the two border cells whose connecting route is the longest, and the
maze is re-carved until that route covers at least MIN_PATH_FACTOR * n*n cells
(half the grid by default). This prevents "complex-looking but trivially solved"
mazes whose entrance and exit happen to sit close together, while the perfect-
maze structure keeps plenty of dead ends and junctions to make the child choose.

Run it (recommended; UV installs the dependency automatically):
    uv run generate_mazes.py

Or with a normal interpreter (needs reportlab: pip install reportlab):
    python3 generate_mazes.py

The drawing code is imported lazily, so the pure maze logic in this module can
be imported and unit-tested without reportlab installed (see test_mazes.py).
"""
import math
import os
import random
import sys
from dataclasses import dataclass
from typing import Optional

# ---------------------------------------------------------------------------
# Tuning knobs
# ---------------------------------------------------------------------------

# Single knob for the OVERALL/AVERAGE difficulty. It shifts the whole scale up
# or down while always keeping a gradual increase from the first to the last
# page. Override at runtime with --difficulty, or edit this value.
# Indicative grid side (first page -> last page):
#     1.0  ->  6x6  -> 12x12   (gentler)
#     2.0  ->  8x8  -> 16x16
#     2.5  ->  9x9  -> 18x18
#     3.0  -> 10x10 -> 20x20   (default)
#     4.0  -> 12x12 -> 24x24   (challenging)
DEFAULT_DIFFICULTY = 3.0
MIN_DIFFICULTY = 1.0
MAX_DIFFICULTY = 10.0

# Safety cap on the grid side so cells stay legible/printable on A4.
MAX_GRID = 40

# Minimum solution length, as a fraction of the cell count (n*n). The entrance
# and exit are placed at the two border cells whose forced route is longest, and
# the maze is re-carved until that route reaches MIN_PATH_FACTOR * n*n cells.
# This rules out "complex-looking but trivially short" mazes where the entrance
# and exit happen to sit next to each other. 0.5 means the child must walk
# through at least half of all cells. (1.0 would require a Hamiltonian path
# visiting every cell, which a random perfect maze cannot guarantee.)
MIN_PATH_FACTOR = 0.5

# Safety cap on how many carvings to try before giving up on the target length.
# Empirically even a 30x30 reaches 0.5*n*n within ~35 carvings, so this is a
# very wide margin; exceeding it raises rather than shipping a too-easy maze.
MAX_GEN_ATTEMPTS = 800

# A4 page size in PostScript points (no reportlab import needed at module load).
PAGE_W = 595.2755905511812   # 210 mm
PAGE_H = 841.8897637795276   # 297 mm

# Maze square geometry on the page.
MAZE_SIDE = 455.0
MAZE_X0 = (PAGE_W - MAZE_SIDE) / 2.0
# Lower the maze a bit to create a safer header band and better page balance.
MAZE_TOP = PAGE_H - 190.0
MAZE_Y0 = MAZE_TOP - MAZE_SIDE

# ---------------------------------------------------------------------------
# Localized content (printed inside the PDF for Italian-speaking children).
# This is product CONTENT, deliberately kept separate from the English code so
# it is easy to translate. Change the strings here to localize the output.
# ---------------------------------------------------------------------------
START_LABEL = "START"            # "START"
GOAL_LABEL = "GOAL"               # "GOAL"
PAGE_LABEL = "Maze {} of {}"   # "Maze {} of {}"
LAST_PAGE_PREFIX = "Ultima sfida: "  # "Final challenge: "
PDF_TITLE = "Mazes for children"

# Coherent (start_icon, goal_icon, title) themes; one is picked at random per page.
THEME_POOL = [
    ("unicorn", "rainbow", "L'unicorno corre verso l'arcobaleno!"),
    ("unicorn", "castle", "L'unicorno torna al castello!"),
    ("unicorn", "crown", "L'unicorno cerca la corona magica!"),
    ("cat", "balloon", "Il gattino insegue il palloncino!"),
    ("cat", "heart", "Porta il gattino fino al cuore!"),
    ("cat", "castle", "Il gattino esplora il castello!"),
    ("bunny", "flower", "Il coniglietto cerca il suo fiore!"),
    ("bunny", "mushroom", "Il coniglietto cerca il fungo nel bosco!"),
    ("bunny", "crown", "Il coniglietto trova la coroncina!"),
    ("butterfly", "flower", "La farfalla vola fino al fiore!"),
    ("butterfly", "rainbow", "La farfalla raggiunge l'arcobaleno!"),
    ("fish", "star", "Il pesciolino segue la stella magica!"),
    ("fish", "heart", "Il pesciolino nuota verso il cuore!"),
    ("flower", "butterfly", "Aiuta la farfalla a trovare il fiore!"),
]
IT_THEME_POOL = THEME_POOL
THEME_POOL = [
    ("unicorn", "rainbow", "The unicorn runs toward the rainbow!"),
    ("unicorn", "castle", "The unicorn returns to the castle!"),
    ("unicorn", "crown", "The unicorn searches for the magic crown!"),
    ("cat", "balloon", "The kitten chases the balloon!"),
    ("cat", "heart", "Guide the kitten to the heart!"),
    ("cat", "castle", "The kitten explores the castle!"),
    ("bunny", "flower", "The bunny is looking for a flower!"),
    ("bunny", "mushroom", "The bunny looks for a mushroom in the woods!"),
    ("bunny", "crown", "The bunny finds a tiny crown!"),
    ("butterfly", "flower", "The butterfly flies to the flower!"),
    ("butterfly", "rainbow", "The butterfly reaches the rainbow!"),
    ("fish", "star", "The little fish follows the magic star!"),
    ("fish", "heart", "The little fish swims to the heart!"),
    ("flower", "butterfly", "Help the butterfly find the flower!"),
]
ES_THEME_POOL = [
    ("unicorn", "rainbow", "¡El unicornio corre hacia el arcoíris!"),
    ("unicorn", "castle", "¡El unicornio vuelve al castillo!"),
    ("unicorn", "crown", "¡El unicornio busca la corona mágica!"),
    ("cat", "balloon", "¡El gatito persigue el globo!"),
    ("cat", "heart", "¡Guía al gatito hasta el corazón!"),
    ("cat", "castle", "¡El gatito explora el castillo!"),
    ("bunny", "flower", "¡El conejito busca su flor!"),
    ("bunny", "mushroom", "¡El conejito busca una seta en el bosque!"),
    ("bunny", "crown", "¡El conejito encuentra una coronita!"),
    ("butterfly", "flower", "¡La mariposa vuela hacia la flor!"),
    ("butterfly", "rainbow", "¡La mariposa llega al arcoíris!"),
    ("fish", "star", "¡El pececito sigue la estrella mágica!"),
    ("fish", "heart", "¡El pececito nada hacia el corazón!"),
    ("flower", "butterfly", "¡Ayuda a la mariposa a encontrar la flor!"),
]
FR_THEME_POOL = [
    ("unicorn", "rainbow", "La licorne court vers l'arc-en-ciel !"),
    ("unicorn", "castle", "La licorne retourne au château !"),
    ("unicorn", "crown", "La licorne cherche la couronne magique !"),
    ("cat", "balloon", "Le chaton poursuit le ballon !"),
    ("cat", "heart", "Guide le chaton vers le cœur !"),
    ("cat", "castle", "Le chaton explore le château !"),
    ("bunny", "flower", "Le lapin cherche sa fleur !"),
    ("bunny", "mushroom", "Le lapin cherche un champignon dans la forêt !"),
    ("bunny", "crown", "Le lapin trouve une petite couronne !"),
    ("butterfly", "flower", "Le papillon vole vers la fleur !"),
    ("butterfly", "rainbow", "Le papillon atteint l'arc-en-ciel !"),
    ("fish", "star", "Le petit poisson suit l'étoile magique !"),
    ("fish", "heart", "Le petit poisson nage vers le cœur !"),
    ("flower", "butterfly", "Aide le papillon à trouver la fleur !"),
]
PT_THEME_POOL = [
    ("unicorn", "rainbow", "O unicórnio corre para o arco-íris!"),
    ("unicorn", "castle", "O unicórnio volta ao castelo!"),
    ("unicorn", "crown", "O unicórnio procura a coroa mágica!"),
    ("cat", "balloon", "O gatinho persegue o balão!"),
    ("cat", "heart", "Leve o gatinho até o coração!"),
    ("cat", "castle", "O gatinho explora o castelo!"),
    ("bunny", "flower", "O coelhinho procura sua flor!"),
    ("bunny", "mushroom", "O coelhinho procura um cogumelo na floresta!"),
    ("bunny", "crown", "O coelhinho encontra uma coroinha!"),
    ("butterfly", "flower", "A borboleta voa até a flor!"),
    ("butterfly", "rainbow", "A borboleta chega ao arco-íris!"),
    ("fish", "star", "O peixinho segue a estrela mágica!"),
    ("fish", "heart", "O peixinho nada até o coração!"),
    ("flower", "butterfly", "Ajude a borboleta a encontrar a flor!"),
]
RU_THEME_POOL = [
    ("unicorn", "rainbow", "Единорог бежит к радуге!"),
    ("unicorn", "castle", "Единорог возвращается в замок!"),
    ("unicorn", "crown", "Единорог ищет волшебную корону!"),
    ("cat", "balloon", "Котёнок гонится за шариком!"),
    ("cat", "heart", "Проведи котёнка к сердечку!"),
    ("cat", "castle", "Котёнок исследует замок!"),
    ("bunny", "flower", "Зайчик ищет свой цветок!"),
    ("bunny", "mushroom", "Зайчик ищет гриб в лесу!"),
    ("bunny", "crown", "Зайчик находит маленькую корону!"),
    ("butterfly", "flower", "Бабочка летит к цветку!"),
    ("butterfly", "rainbow", "Бабочка долетает до радуги!"),
    ("fish", "star", "Рыбка следует за волшебной звездой!"),
    ("fish", "heart", "Рыбка плывёт к сердечку!"),
    ("flower", "butterfly", "Помоги бабочке найти цветок!"),
]
ZH_THEME_POOL = [
    ("unicorn", "rainbow", "独角兽奔向彩虹！"),
    ("unicorn", "castle", "独角兽回到城堡！"),
    ("unicorn", "crown", "独角兽寻找魔法皇冠！"),
    ("cat", "balloon", "小猫追着气球跑！"),
    ("cat", "heart", "带小猫找到爱心！"),
    ("cat", "castle", "小猫探索城堡！"),
    ("bunny", "flower", "小兔子寻找花朵！"),
    ("bunny", "mushroom", "小兔子在森林里找蘑菇！"),
    ("bunny", "crown", "小兔子找到小皇冠！"),
    ("butterfly", "flower", "蝴蝶飞向花朵！"),
    ("butterfly", "rainbow", "蝴蝶飞到彩虹边！"),
    ("fish", "star", "小鱼跟着魔法星星走！"),
    ("fish", "heart", "小鱼游向爱心！"),
    ("flower", "butterfly", "帮助蝴蝶找到花朵！"),
]
HI_THEME_POOL = [
    ("unicorn", "rainbow", "यूनिकॉर्न इंद्रधनुष की ओर दौड़ रहा है!"),
    ("unicorn", "castle", "यूनिकॉर्न किले में लौट रहा है!"),
    ("unicorn", "crown", "यूनिकॉर्न जादुई मुकुट ढूँढ रहा है!"),
    ("cat", "balloon", "बिल्ली का बच्चा गुब्बारे के पीछे भाग रहा है!"),
    ("cat", "heart", "बिल्ली के बच्चे को दिल तक पहुँचाओ!"),
    ("cat", "castle", "बिल्ली का बच्चा किला खोज रहा है!"),
    ("bunny", "flower", "खरगोश अपना फूल ढूँढ रहा है!"),
    ("bunny", "mushroom", "खरगोश जंगल में मशरूम ढूँढ रहा है!"),
    ("bunny", "crown", "खरगोश को छोटा मुकुट मिलता है!"),
    ("butterfly", "flower", "तितली फूल तक उड़ती है!"),
    ("butterfly", "rainbow", "तितली इंद्रधनुष तक पहुँचती है!"),
    ("fish", "star", "छोटी मछली जादुई तारे का पीछा करती है!"),
    ("fish", "heart", "छोटी मछली दिल की ओर तैरती है!"),
    ("flower", "butterfly", "तितली को फूल ढूँढने में मदद करो!"),
]
AR_THEME_POOL = [
    ("unicorn", "rainbow", "حيوان وحيد القرن يركض نحو قوس قزح!"),
    ("unicorn", "castle", "حيوان وحيد القرن يعود إلى القلعة!"),
    ("unicorn", "crown", "حيوان وحيد القرن يبحث عن التاج السحري!"),
    ("cat", "balloon", "القطة الصغيرة تطارد البالون!"),
    ("cat", "heart", "ساعد القطة الصغيرة للوصول إلى القلب!"),
    ("cat", "castle", "القطة الصغيرة تستكشف القلعة!"),
    ("bunny", "flower", "الأرنب الصغير يبحث عن زهرة!"),
    ("bunny", "mushroom", "الأرنب الصغير يبحث عن فطر في الغابة!"),
    ("bunny", "crown", "الأرنب الصغير يجد تاجًا صغيرًا!"),
    ("butterfly", "flower", "الفراشة تطير نحو الزهرة!"),
    ("butterfly", "rainbow", "الفراشة تصل إلى قوس قزح!"),
    ("fish", "star", "السمكة الصغيرة تتبع النجمة السحرية!"),
    ("fish", "heart", "السمكة الصغيرة تسبح نحو القلب!"),
    ("flower", "butterfly", "ساعد الفراشة في العثور على الزهرة!"),
]
BN_THEME_POOL = [
    ("unicorn", "rainbow", "ইউনিকর্ন রামধনুর দিকে দৌড়াচ্ছে!"),
    ("unicorn", "castle", "ইউনিকর্ন দুর্গে ফিরছে!"),
    ("unicorn", "crown", "ইউনিকর্ন জাদুর মুকুট খুঁজছে!"),
    ("cat", "balloon", "বিড়ালছানা বেলুনের পেছনে দৌড়াচ্ছে!"),
    ("cat", "heart", "বিড়ালছানাকে হৃদয়ের কাছে নিয়ে যাও!"),
    ("cat", "castle", "বিড়ালছানা দুর্গ ঘুরে দেখছে!"),
    ("bunny", "flower", "খরগোশটি ফুল খুঁজছে!"),
    ("bunny", "mushroom", "খরগোশটি বনে মাশরুম খুঁজছে!"),
    ("bunny", "crown", "খরগোশটি ছোট মুকুট পেয়েছে!"),
    ("butterfly", "flower", "প্রজাপতি ফুলের দিকে উড়ছে!"),
    ("butterfly", "rainbow", "প্রজাপতি রামধনুতে পৌঁছায়!"),
    ("fish", "star", "ছোট মাছটি জাদুর তারা অনুসরণ করছে!"),
    ("fish", "heart", "ছোট মাছটি হৃদয়ের দিকে সাঁতরাচ্ছে!"),
    ("flower", "butterfly", "প্রজাপতিকে ফুল খুঁজে পেতে সাহায্য করো!"),
]

# Locale bundles used by the rendering pipeline.
UNICODE_FONT_NAME = "UniversalUnicode"
UNICODE_FONT_CANDIDATES = [
    "/Library/Fonts/Arial Unicode.ttf",
    "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
]

LOCALIZATIONS = {
    "en": {
        "start_label": "START",
        "goal_label": "GOAL",
        "page_label": "Maze {} of {}",
        "last_page_prefix": "Final challenge: ",
        "pdf_title": "Mazes for children 4-6 years old",
        "theme_pool": THEME_POOL,
        "title_font": "Helvetica-Bold",
        "label_font": "Helvetica-Bold",
        "footer_font": "Helvetica",
    },
    "it": {
        "start_label": "PARTENZA",
        "goal_label": "ARRIVO",
        "page_label": "Labirinto {} di {}",
        "last_page_prefix": "Ultima sfida: ",
        "pdf_title": "Labirinti per bambini 4-6 anni",
        "theme_pool": IT_THEME_POOL,
    },
    "zh": {
        "start_label": "开始",
        "goal_label": "终点",
        "page_label": "迷宫 {} / {}",
        "last_page_prefix": "最终挑战：",
        "pdf_title": "4-6岁儿童迷宫",
        "theme_pool": ZH_THEME_POOL,
        # Built-in CID font in reportlab for Chinese glyph coverage.
        "title_font": "STSong-Light",
        "label_font": "STSong-Light",
        "footer_font": "STSong-Light",
    },
    "hi": {
        "start_label": "शुरुआत",
        "goal_label": "मंज़िल",
        "page_label": "भूलभुलैया {} / {}",
        "last_page_prefix": "अंतिम चुनौती: ",
        "pdf_title": "4-6 साल के बच्चों के लिए भूलभुलैया",
        "theme_pool": HI_THEME_POOL,
        "title_font": UNICODE_FONT_NAME,
        "label_font": UNICODE_FONT_NAME,
        "footer_font": UNICODE_FONT_NAME,
    },
    "es": {
        "start_label": "INICIO",
        "goal_label": "LLEGADA",
        "page_label": "Laberinto {} de {}",
        "last_page_prefix": "Desafío final: ",
        "pdf_title": "Laberintos para niños de 4-6 años",
        "theme_pool": ES_THEME_POOL,
        "title_font": "Helvetica-Bold",
        "label_font": "Helvetica-Bold",
        "footer_font": "Helvetica",
    },
    "fr": {
        "start_label": "DÉPART",
        "goal_label": "ARRIVÉE",
        "page_label": "Labyrinthe {} sur {}",
        "last_page_prefix": "Défi final : ",
        "pdf_title": "Labyrinthes pour enfants de 4 à 6 ans",
        "theme_pool": FR_THEME_POOL,
        "title_font": "Helvetica-Bold",
        "label_font": "Helvetica-Bold",
        "footer_font": "Helvetica",
    },
    "ar": {
        "start_label": "البداية",
        "goal_label": "النهاية",
        "page_label": "المتاهة {} من {}",
        "last_page_prefix": "التحدي الأخير: ",
        "pdf_title": "متاهات للأطفال من 4 إلى 6 سنوات",
        "theme_pool": AR_THEME_POOL,
        "title_font": UNICODE_FONT_NAME,
        "label_font": UNICODE_FONT_NAME,
        "footer_font": UNICODE_FONT_NAME,
    },
    "bn": {
        "start_label": "শুরু",
        "goal_label": "শেষ",
        "page_label": "গোলকধাঁধা {} / {}",
        "last_page_prefix": "শেষ চ্যালেঞ্জ: ",
        "pdf_title": "৪-৬ বছরের শিশুদের জন্য গোলকধাঁধা",
        "theme_pool": BN_THEME_POOL,
        "title_font": UNICODE_FONT_NAME,
        "label_font": UNICODE_FONT_NAME,
        "footer_font": UNICODE_FONT_NAME,
    },
    "pt": {
        "start_label": "INÍCIO",
        "goal_label": "CHEGADA",
        "page_label": "Labirinto {} de {}",
        "last_page_prefix": "Desafio final: ",
        "pdf_title": "Labirintos para crianças de 4-6 anos",
        "theme_pool": PT_THEME_POOL,
        "title_font": "Helvetica-Bold",
        "label_font": "Helvetica-Bold",
        "footer_font": "Helvetica",
    },
    "ru": {
        "start_label": "СТАРТ",
        "goal_label": "ФИНИШ",
        "page_label": "Лабиринт {} из {}",
        "last_page_prefix": "Финальное испытание: ",
        "pdf_title": "Лабиринты для детей 4–6 лет",
        "theme_pool": RU_THEME_POOL,
        "title_font": UNICODE_FONT_NAME,
        "label_font": UNICODE_FONT_NAME,
        "footer_font": UNICODE_FONT_NAME,
    },
    "de": {
        "start_label": "START",
        "goal_label": "ZIEL",
        "page_label": "Labyrinth {} von {}",
        "last_page_prefix": "Letzte Herausforderung: ",
        "pdf_title": "Labyrinthe für Kinder von 4–6 Jahren",
        "theme_pool": THEME_POOL,
        "title_font": "Helvetica-Bold",
        "label_font": "Helvetica-Bold",
        "footer_font": "Helvetica",
    },
    "uk": {
        "start_label": "СТАРТ",
        "goal_label": "ФІНІШ",
        "page_label": "Лабіринт {} з {}",
        "last_page_prefix": "Фінальний виклик: ",
        "pdf_title": "Лабіринти для дітей 4–6 років",
        "theme_pool": THEME_POOL,
        "title_font": UNICODE_FONT_NAME,
        "label_font": UNICODE_FONT_NAME,
        "footer_font": UNICODE_FONT_NAME,
    },
    "ro": {
        "start_label": "START",
        "goal_label": "SOSIRE",
        "page_label": "Labirint {} din {}",
        "last_page_prefix": "Provocarea finală: ",
        "pdf_title": "Labirinturi pentru copii de 4–6 ani",
        "theme_pool": THEME_POOL,
        "title_font": UNICODE_FONT_NAME,
        "label_font": UNICODE_FONT_NAME,
        "footer_font": UNICODE_FONT_NAME,
    },
    "pl": {
        "start_label": "START",
        "goal_label": "META",
        "page_label": "Labirynt {} z {}",
        "last_page_prefix": "Ostatnie wyzwanie: ",
        "pdf_title": "Labirynty dla dzieci 4–6 lat",
        "theme_pool": THEME_POOL,
        "title_font": UNICODE_FONT_NAME,
        "label_font": UNICODE_FONT_NAME,
        "footer_font": UNICODE_FONT_NAME,
    },
    "el": {
        "start_label": "ΑΡΧΗ",
        "goal_label": "ΤΕΡΜΑ",
        "page_label": "Λαβύρινθος {} από {}",
        "last_page_prefix": "Τελική πρόκληση: ",
        "pdf_title": "Λαβύρινθοι για παιδιά 4–6 ετών",
        "theme_pool": THEME_POOL,
        "title_font": UNICODE_FONT_NAME,
        "label_font": UNICODE_FONT_NAME,
        "footer_font": UNICODE_FONT_NAME,
    },
}
DEFAULT_LOCALE = "en"


def get_localization(locale):
    """Return localization bundle for `locale`."""
    try:
        return LOCALIZATIONS[locale]
    except KeyError as exc:
        supported = ", ".join(sorted(LOCALIZATIONS))
        raise ValueError("unknown locale %r (supported: %s)" % (locale, supported)) from exc


def _register_locale_fonts(loc, pdfmetrics, UnicodeCIDFont, TTFont):
    """Register fonts required by locale config."""
    for key in ("title_font", "label_font", "footer_font"):
        font_name = loc.get(key)
        if font_name == "STSong-Light":
            try:
                pdfmetrics.getFont(font_name)
            except KeyError:
                pdfmetrics.registerFont(UnicodeCIDFont(font_name))
        elif font_name == UNICODE_FONT_NAME:
            try:
                pdfmetrics.getFont(font_name)
                continue
            except KeyError:
                pass
            path = next((p for p in UNICODE_FONT_CANDIDATES if os.path.exists(p)), None)
            if path is None:
                # CI containers and minimal Linux images may not include our preferred
                # Unicode fonts. Register a Latin fallback so PDF generation continues.
                from reportlab.pdfbase.pdfmetrics import Font

                pdfmetrics.registerFont(Font(font_name, "Helvetica", "WinAnsiEncoding"))
                continue
            pdfmetrics.registerFont(TTFont(font_name, path))

# Small decorative motifs scattered in the page margins.
MARGIN_MOTIFS = ["star", "heart", "flower", "cloud"]


# ===========================================================================
# Pure maze logic (no reportlab dependency -> unit-testable on its own)
# ===========================================================================
def generate_maze(cols, rows, rng):
    """Carve a "perfect" maze with the recursive-backtracker algorithm.

    Returns two boolean grids describing the OPEN passages between cells:
        right[r][c]  True  -> open passage between (r, c) and (r, c+1)
        down[r][c]   True  -> open passage between (r, c) and (r+1, c)

    The starting cell is random, so the carved paths differ on every run.
    The result is a spanning tree (exactly one path between any two cells).
    """
    visited = [[False] * cols for _ in range(rows)]
    right = [[False] * cols for _ in range(rows)]
    down = [[False] * cols for _ in range(rows)]

    start_r, start_c = rng.randrange(rows), rng.randrange(cols)
    stack = [(start_r, start_c)]
    visited[start_r][start_c] = True

    while stack:
        r, c = stack[-1]
        # Collect unvisited orthogonal neighbours.
        neighbours = []
        if r > 0 and not visited[r - 1][c]:
            neighbours.append(("U", r - 1, c))
        if r < rows - 1 and not visited[r + 1][c]:
            neighbours.append(("D", r + 1, c))
        if c > 0 and not visited[r][c - 1]:
            neighbours.append(("L", r, c - 1))
        if c < cols - 1 and not visited[r][c + 1]:
            neighbours.append(("R", r, c + 1))

        if not neighbours:
            stack.pop()  # dead end: backtrack
            continue

        direction, nr, nc = rng.choice(neighbours)
        # Open the wall between the current cell and the chosen neighbour.
        if direction == "U":
            down[nr][nc] = True
        elif direction == "D":
            down[r][c] = True
        elif direction == "L":
            right[nr][nc] = True
        else:  # "R"
            right[r][c] = True

        visited[nr][nc] = True
        stack.append((nr, nc))

    return right, down


def count_open_passages(right, down):
    """Total number of open passages between adjacent cells."""
    return sum(sum(row) for row in right) + sum(sum(row) for row in down)


def opening_to_cell(spec, rows, cols):
    """Map an (edge, index) opening to the border cell it sits on."""
    edge, idx = spec
    if edge == "top":
        return (0, idx)
    if edge == "bottom":
        return (rows - 1, idx)
    if edge == "left":
        return (idx, 0)
    if edge == "right":
        return (idx, cols - 1)
    raise ValueError("unknown edge: %r" % (edge,))


def find_path(right, down, rows, cols, start, goal):
    """Breadth-first search through the open passages.

    Returns the list of cells from `start` to `goal`, or None if unreachable.
    For a perfect maze a path always exists between any two cells.
    """
    from collections import deque

    prev = {start: None}
    queue = deque([start])
    while queue:
        r, c = queue.popleft()
        if (r, c) == goal:
            # Reconstruct the path back to the start.
            path = []
            cur = goal
            while cur is not None:
                path.append(cur)
                cur = prev[cur]
            path.reverse()
            return path
        # Expand through open passages only.
        if c < cols - 1 and right[r][c] and (r, c + 1) not in prev:
            prev[(r, c + 1)] = (r, c)
            queue.append((r, c + 1))
        if c > 0 and right[r][c - 1] and (r, c - 1) not in prev:
            prev[(r, c - 1)] = (r, c)
            queue.append((r, c - 1))
        if r < rows - 1 and down[r][c] and (r + 1, c) not in prev:
            prev[(r + 1, c)] = (r, c)
            queue.append((r + 1, c))
        if r > 0 and down[r - 1][c] and (r - 1, c) not in prev:
            prev[(r - 1, c)] = (r, c)
            queue.append((r - 1, c))
    return None


def bfs_distances(right, down, rows, cols, src):
    """Shortest-path distance, in cells, from `src` to every reachable cell.

    Returns a dict {cell: distance}. In a perfect maze every cell is reachable,
    so the result covers the whole grid.
    """
    from collections import deque

    dist = {src: 0}
    queue = deque([src])
    while queue:
        r, c = queue.popleft()
        d = dist[(r, c)]
        if c < cols - 1 and right[r][c] and (r, c + 1) not in dist:
            dist[(r, c + 1)] = d + 1
            queue.append((r, c + 1))
        if c > 0 and right[r][c - 1] and (r, c - 1) not in dist:
            dist[(r, c - 1)] = d + 1
            queue.append((r, c - 1))
        if r < rows - 1 and down[r][c] and (r + 1, c) not in dist:
            dist[(r + 1, c)] = d + 1
            queue.append((r + 1, c))
        if r > 0 and down[r - 1][c] and (r - 1, c) not in dist:
            dist[(r - 1, c)] = d + 1
            queue.append((r - 1, c))
    return dist


def cell_to_opening(cell, rows, cols):
    """Map a border cell to the (edge, idx) opening sitting on it.

    Inverse of `opening_to_cell`. Corner cells are resolved to a horizontal
    edge (top/bottom) before a vertical one (left/right).
    """
    r, c = cell
    if r == 0:
        return ("top", c)
    if r == rows - 1:
        return ("bottom", c)
    if c == 0:
        return ("left", r)
    if c == cols - 1:
        return ("right", r)
    raise ValueError("cell %r is not on the border" % (cell,))


def count_dead_ends_and_junctions(right, down, rows, cols):
    """Count dead ends (cells with a single passage) and junctions (>= 3).

    A maze with many dead ends and junctions forces real choices and
    backtracking instead of offering one obvious corridor.
    """
    dead = junc = 0
    for r in range(rows):
        for c in range(cols):
            k = 0
            if c < cols - 1 and right[r][c]:
                k += 1
            if c > 0 and right[r][c - 1]:
                k += 1
            if r < rows - 1 and down[r][c]:
                k += 1
            if r > 0 and down[r - 1][c]:
                k += 1
            if k == 1:
                dead += 1
            elif k >= 3:
                junc += 1
    return dead, junc


def longest_border_solution(right, down, rows, cols):
    """Find the entrance/exit border cells whose connecting route is longest.

    Entrance candidates are the top/left border cells and exit candidates the
    bottom/right border cells, preserving a natural top-left to bottom-right
    flow. Returns (entrance_cell, exit_cell, path_length_in_cells).
    """
    entrances = {(0, c) for c in range(cols)} | {(r, 0) for r in range(rows)}
    exits = {(rows - 1, c) for c in range(cols)} | {(r, cols - 1) for r in range(rows)}
    best_entrance = best_exit = None
    best_len = -1
    for s in entrances:
        dist = bfs_distances(right, down, rows, cols, s)
        for e in exits:
            if e == s:
                continue
            d = dist.get(e)
            if d is not None and d + 1 > best_len:
                best_len = d + 1
                best_entrance, best_exit = s, e
    return best_entrance, best_exit, best_len


def min_solution_length(n, min_path_factor=MIN_PATH_FACTOR):
    """Guaranteed minimum solution length, in cells, for an n x n maze."""
    return math.ceil(min_path_factor * n * n)


def generate_long_maze(n, rng, min_len=None, min_path_factor=MIN_PATH_FACTOR):
    """Carve an n x n perfect maze with a guaranteed-long forced solution.

    For each carving the farthest (top/left)-entrance to (bottom/right)-exit
    border pair is selected, which maximises the length of the unique route.
    Carving is retried until that route reaches `min_len` cells (default
    `min_solution_length(n)`), so the maze can never collapse into a short hop
    from entrance to exit. Because it stays a perfect maze, it still has the
    dead ends and junctions of a recursive-backtracker carving.

    Returns (right, down, entrance_opening, exit_opening, path_length).
    If the target cannot be met within MAX_GEN_ATTEMPTS, it falls back to the
    best maze found and emits a warning to stderr instead of failing the run.
    """
    if min_len is None:
        min_len = min_solution_length(n, min_path_factor)

    best = None  # (length, right, down, entrance_cell, exit_cell)
    for _ in range(MAX_GEN_ATTEMPTS):
        right, down = generate_maze(n, n, rng)
        entrance_cell, exit_cell, length = longest_border_solution(right, down, n, n)
        if best is None or length > best[0]:
            best = (length, right, down, entrance_cell, exit_cell)
        if length >= min_len:
            break

    length, right, down, entrance_cell, exit_cell = best
    if length < min_len:
        got_factor = length / float(n * n)
        req_factor = min_len / float(n * n)
        print(
            "warning: %dx%d maze could not reach requested solution length "
            "(required >= %d cells, best %d in %d attempts; got factor %.3f, "
            "requested %.3f). Using best found maze."
            % (n, n, min_len, length, MAX_GEN_ATTEMPTS, got_factor, req_factor),
            file=sys.stderr,
        )

    entrance = cell_to_opening(entrance_cell, n, n)
    exit_ = cell_to_opening(exit_cell, n, n)
    return right, down, entrance, exit_, length


def choose_openings(n, rng):
    """Pick a random entrance and exit on the maze border.

    Entrance goes on the top or left edge, exit on the bottom or right edge,
    which keeps a natural top-left to bottom-right flow for young children.
    Returns ((entrance_edge, idx), (exit_edge, idx)).
    """
    entrance = (rng.choice(["top", "left"]), rng.randrange(n))
    exit_ = (rng.choice(["bottom", "right"]), rng.randrange(n))
    return entrance, exit_


def grid_sizes(pages, difficulty):
    """Per-page grid side, increasing across pages and scaled by difficulty.

    `difficulty` raises/lowers both the first-page minimum and the last-page
    maximum, so the average difficulty changes while the page-to-page gradient
    is preserved. Sizes are clamped to [4, MAX_GRID].
    """
    min_n = round(4 + 2 * difficulty)   # first page side
    max_n = round(8 + 4 * difficulty)   # last page side
    min_n = max(4, min(min_n, MAX_GRID))
    max_n = max(min_n + 1, min(max_n, MAX_GRID))

    sizes = []
    for i in range(pages):
        frac = i / max(1, pages - 1)
        sizes.append(int(round(min_n + frac * (max_n - min_n))))
    return sizes


# ===========================================================================
# Drawing helpers (operate on a reportlab canvas passed in as `c`)
# All shapes are outline-only line-art -> clean black-and-white printing.
# ===========================================================================
def _setup(c, lw):
    """Common stroke/fill setup for a line-art shape."""
    c.setLineWidth(lw)
    c.setLineCap(1)
    c.setLineJoin(1)
    c.setStrokeColorRGB(0, 0, 0)
    c.setFillColorRGB(0, 0, 0)


def draw_star(c, cx, cy, s, n=5, rot=90, lw=1.4, fill=False):
    """Five-pointed star centred at (cx, cy)."""
    _setup(c, lw)
    r_out, r_in = s, s * 0.42
    p = c.beginPath()
    for i in range(n * 2):
        ang = math.radians(rot + i * 180.0 / n)
        r = r_out if i % 2 == 0 else r_in
        x, y = cx + r * math.cos(ang), cy + r * math.sin(ang)
        p.moveTo(x, y) if i == 0 else p.lineTo(x, y)
    p.close()
    c.drawPath(p, stroke=1, fill=1 if fill else 0)


def draw_heart(c, cx, cy, s, lw=1.4, fill=False):
    """Heart shape built from two Bezier lobes."""
    _setup(c, lw)
    p = c.beginPath()
    p.moveTo(cx, cy - s * 0.75)
    p.curveTo(cx - s * 0.55, cy - s * 0.15, cx - s * 1.05, cy + s * 0.55,
              cx - s * 0.5, cy + s * 0.95)
    p.curveTo(cx - s * 0.2, cy + s * 1.18, cx - s * 0.05, cy + s * 0.75,
              cx, cy + s * 0.55)
    p.curveTo(cx + s * 0.05, cy + s * 0.75, cx + s * 0.2, cy + s * 1.18,
              cx + s * 0.5, cy + s * 0.95)
    p.curveTo(cx + s * 1.05, cy + s * 0.55, cx + s * 0.55, cy - s * 0.15,
              cx, cy - s * 0.75)
    p.close()
    c.drawPath(p, stroke=1, fill=1 if fill else 0)


def draw_flower(c, cx, cy, s, petals=5, lw=1.4):
    """Simple flower: ring of petals around a filled centre."""
    _setup(c, lw)
    petal_r, dist = s * 0.55, s * 0.55
    for i in range(petals):
        ang = math.radians(90 + i * 360.0 / petals)
        c.circle(cx + dist * math.cos(ang), cy + dist * math.sin(ang),
                 petal_r, stroke=1, fill=0)
    c.circle(cx, cy, s * 0.32, stroke=1, fill=1)
    c.setFillColorRGB(0, 0, 0)


def draw_butterfly(c, cx, cy, s, lw=1.4):
    """Butterfly: body, four wings, dots and antennae."""
    _setup(c, lw)
    c.ellipse(cx - s * 0.07, cy - s * 0.7, cx + s * 0.07, cy + s * 0.7,
              stroke=1, fill=1)
    c.setFillColorRGB(0, 0, 0)
    c.ellipse(cx - s * 0.95, cy + s * 0.05, cx - s * 0.05, cy + s * 0.85, stroke=1, fill=0)
    c.ellipse(cx + s * 0.05, cy + s * 0.05, cx + s * 0.95, cy + s * 0.85, stroke=1, fill=0)
    c.ellipse(cx - s * 0.8, cy - s * 0.75, cx - s * 0.05, cy - s * 0.02, stroke=1, fill=0)
    c.ellipse(cx + s * 0.05, cy - s * 0.75, cx + s * 0.8, cy - s * 0.02, stroke=1, fill=0)
    c.circle(cx - s * 0.5, cy + s * 0.45, s * 0.12, stroke=1, fill=0)
    c.circle(cx + s * 0.5, cy + s * 0.45, s * 0.12, stroke=1, fill=0)
    c.line(cx - s * 0.05, cy + s * 0.7, cx - s * 0.35, cy + s * 1.15)
    c.line(cx + s * 0.05, cy + s * 0.7, cx + s * 0.35, cy + s * 1.15)
    c.circle(cx - s * 0.35, cy + s * 1.2, s * 0.07, stroke=1, fill=1)
    c.circle(cx + s * 0.35, cy + s * 1.2, s * 0.07, stroke=1, fill=1)
    c.setFillColorRGB(0, 0, 0)


def draw_cloud(c, cx, cy, s, lw=1.4):
    """Puffy cloud outline."""
    _setup(c, lw)
    p = c.beginPath()
    p.arc(cx - s, cy - s * 0.4, cx - s * 0.2, cy + s * 0.4, 90, 180)
    p.arcTo(cx - s * 0.7, cy - s * 0.2, cx + s * 0.1, cy + s * 0.85, 120, 120)
    p.arcTo(cx - s * 0.1, cy - s * 0.2, cx + s * 0.8, cy + s * 0.9, 80, 100)
    p.arcTo(cx + s * 0.3, cy - s * 0.3, cx + s * 1.05, cy + s * 0.45, 60, 130)
    c.drawPath(p, stroke=1, fill=0)
    c.line(cx - s * 0.95, cy - s * 0.35, cx + s * 0.95, cy - s * 0.35)


def draw_rainbow(c, cx, cy, s, lw=1.6):
    """Rainbow arcs with a little cloud at each end."""
    _setup(c, lw)
    for k in range(4):
        r = s * (1.0 - k * 0.18)
        c.arc(cx - r, cy - r, cx + r, cy + r, 0, 180)
    draw_cloud(c, cx - s * 0.95, cy - s * 0.05, s * 0.4, lw)
    draw_cloud(c, cx + s * 0.95, cy - s * 0.05, s * 0.4, lw)


def draw_crown(c, cx, cy, s, lw=1.5):
    """Three-peaked crown with jewels."""
    _setup(c, lw)
    p = c.beginPath()
    p.moveTo(cx - s, cy - s * 0.6)
    p.lineTo(cx - s, cy + s * 0.4)
    p.lineTo(cx - s * 0.5, cy - s * 0.1)
    p.lineTo(cx, cy + s * 0.7)
    p.lineTo(cx + s * 0.5, cy - s * 0.1)
    p.lineTo(cx + s, cy + s * 0.4)
    p.lineTo(cx + s, cy - s * 0.6)
    p.close()
    c.drawPath(p, stroke=1, fill=0)
    c.line(cx - s, cy - s * 0.6, cx + s, cy - s * 0.6)
    for dx in (-1, 0, 1):
        c.circle(cx + dx * s, cy + (0.7 if dx == 0 else 0.4) * s, s * 0.12,
                 stroke=1, fill=1)
    c.setFillColorRGB(0, 0, 0)


def draw_castle(c, cx, cy, s, lw=1.5):
    """Fairy-tale castle: central keep, two towers, flags and a door."""
    _setup(c, lw)
    b = s * 1.3
    base_y = cy - s
    c.rect(cx - b * 0.45, base_y, b * 0.9, s * 1.4, stroke=1, fill=0)
    for sx in (-1, 1):
        tx = cx + sx * b * 0.55
        c.rect(tx - s * 0.28, base_y, s * 0.56, s * 1.9, stroke=1, fill=0)
        for k in (-1, 0, 1):  # tower battlements
            c.rect(tx - s * 0.28 + (k + 1) * s * 0.187, base_y + s * 1.9,
                   s * 0.13, s * 0.18, stroke=1, fill=0)
        c.line(tx, base_y + s * 2.08, tx, base_y + s * 2.6)  # flagpole
        fp = c.beginPath()
        fp.moveTo(tx, base_y + s * 2.6)
        fp.lineTo(tx + s * 0.4, base_y + s * 2.48)
        fp.lineTo(tx, base_y + s * 2.36)
        fp.close()
        c.drawPath(fp, stroke=1, fill=0)
    for k in range(4):  # keep battlements
        c.rect(cx - b * 0.45 + k * (b * 0.9 / 4) + b * 0.9 / 16,
               base_y + s * 1.4, b * 0.9 / 8, s * 0.18, stroke=1, fill=0)
    dw = s * 0.34  # arched door
    c.rect(cx - dw, base_y, 2 * dw, s * 0.55, stroke=1, fill=0)
    c.arc(cx - dw, base_y + s * 0.2, cx + dw, base_y + s * 0.9, 0, 180)
    draw_star(c, cx, base_y + s * 0.95, s * 0.18, lw=lw * 0.8)


def draw_unicorn(c, cx, cy, s, lw=1.5):
    """Cute three-quarter unicorn head with horn and mane."""
    _setup(c, lw)
    p = c.beginPath()
    p.moveTo(cx - s * 0.55, cy + s * 0.2)
    p.curveTo(cx - s * 0.75, cy - s * 0.55, cx - s * 0.35, cy - s * 1.0,
              cx + s * 0.15, cy - s * 0.95)
    p.curveTo(cx + s * 0.55, cy - s * 0.9, cx + s * 0.6, cy - s * 0.4,
              cx + s * 0.5, cy + s * 0.1)
    p.curveTo(cx + s * 0.45, cy + s * 0.5, cx + s * 0.2, cy + s * 0.7,
              cx - s * 0.1, cy + s * 0.65)
    p.curveTo(cx - s * 0.35, cy + s * 0.6, cx - s * 0.5, cy + s * 0.45,
              cx - s * 0.55, cy + s * 0.2)
    p.close()
    c.drawPath(p, stroke=1, fill=0)
    c.circle(cx + s * 0.02, cy - s * 0.78, s * 0.05, stroke=1, fill=1)  # nostril
    c.setFillColorRGB(0, 0, 0)
    sm = c.beginPath()  # mouth
    sm.moveTo(cx + s * 0.18, cy - s * 0.78)
    sm.curveTo(cx + s * 0.32, cy - s * 0.7, cx + s * 0.34, cy - s * 0.55,
               cx + s * 0.28, cy - s * 0.45)
    c.drawPath(sm, stroke=1, fill=0)
    eye = c.beginPath()  # happy closed eye
    eye.moveTo(cx - s * 0.02, cy - s * 0.18)
    eye.curveTo(cx + s * 0.08, cy - s * 0.02, cx + s * 0.24, cy - s * 0.02,
                cx + s * 0.32, cy - s * 0.18)
    c.drawPath(eye, stroke=1, fill=0)
    ear = c.beginPath()
    ear.moveTo(cx + s * 0.35, cy + s * 0.55)
    ear.lineTo(cx + s * 0.62, cy + s * 0.85)
    ear.lineTo(cx + s * 0.55, cy + s * 0.45)
    ear.close()
    c.drawPath(ear, stroke=1, fill=0)
    horn = c.beginPath()
    horn.moveTo(cx + s * 0.02, cy + s * 0.62)
    horn.lineTo(cx + s * 0.18, cy + s * 1.35)
    horn.lineTo(cx + s * 0.26, cy + s * 0.58)
    horn.close()
    c.drawPath(horn, stroke=1, fill=0)
    for k in range(1, 4):  # horn spiral ticks
        yy = cy + s * (0.62 + k * 0.18)
        c.line(cx + s * 0.06, yy, cx + s * 0.24, yy + s * 0.04)
    mane = c.beginPath()
    mane.moveTo(cx - s * 0.1, cy + s * 0.65)
    mane.curveTo(cx - s * 0.5, cy + s * 0.55, cx - s * 0.55, cy + s * 0.1,
                 cx - s * 0.75, cy - s * 0.1)
    mane.curveTo(cx - s * 0.5, cy - s * 0.05, cx - s * 0.45, cy - s * 0.3,
                 cx - s * 0.7, cy - s * 0.6)
    mane.curveTo(cx - s * 0.4, cy - s * 0.5, cx - s * 0.45, cy - s * 0.7,
                 cx - s * 0.55, cy - s * 0.95)
    c.drawPath(mane, stroke=1, fill=0)


def draw_cat(c, cx, cy, s, lw=1.5):
    """Round cat face with ears, eyes, nose and whiskers."""
    _setup(c, lw)
    c.circle(cx, cy, s, stroke=1, fill=0)
    for sx in (-1, 1):
        ear = c.beginPath()
        ear.moveTo(cx + sx * s * 0.55, cy + s * 0.55)
        ear.lineTo(cx + sx * s * 0.85, cy + s * 1.15)
        ear.lineTo(cx + sx * s * 0.2, cy + s * 0.85)
        ear.close()
        c.drawPath(ear, stroke=1, fill=0)
    for sx in (-1, 1):
        c.circle(cx + sx * s * 0.38, cy + s * 0.12, s * 0.1, stroke=1, fill=1)
    c.setFillColorRGB(0, 0, 0)
    nose = c.beginPath()
    nose.moveTo(cx - s * 0.12, cy - s * 0.12)
    nose.lineTo(cx + s * 0.12, cy - s * 0.12)
    nose.lineTo(cx, cy - s * 0.3)
    nose.close()
    c.drawPath(nose, stroke=1, fill=1)
    c.setFillColorRGB(0, 0, 0)
    mouth = c.beginPath()
    mouth.moveTo(cx, cy - s * 0.3)
    mouth.curveTo(cx - s * 0.05, cy - s * 0.45, cx - s * 0.2, cy - s * 0.45, cx - s * 0.28, cy - s * 0.38)
    mouth.moveTo(cx, cy - s * 0.3)
    mouth.curveTo(cx + s * 0.05, cy - s * 0.45, cx + s * 0.2, cy - s * 0.45, cx + s * 0.28, cy - s * 0.38)
    c.drawPath(mouth, stroke=1, fill=0)
    for sy in (0.0, 0.15, -0.15):  # whiskers
        c.line(cx - s * 0.45, cy - s * 0.12 + s * sy, cx - s * 1.05, cy - s * 0.05 + s * sy * 1.3)
        c.line(cx + s * 0.45, cy - s * 0.12 + s * sy, cx + s * 1.05, cy - s * 0.05 + s * sy * 1.3)


def draw_bunny(c, cx, cy, s, lw=1.5):
    """Round bunny face with two long ears."""
    _setup(c, lw)
    c.circle(cx, cy, s, stroke=1, fill=0)
    for sx in (-1, 1):
        c.ellipse(cx + sx * s * 0.55 - s * 0.22, cy + s * 0.8,
                  cx + sx * s * 0.55 + s * 0.22, cy + s * 2.1, stroke=1, fill=0)
        c.ellipse(cx + sx * s * 0.55 - s * 0.1, cy + s * 1.0,
                  cx + sx * s * 0.55 + s * 0.1, cy + s * 1.9, stroke=1, fill=0)
    for sx in (-1, 1):
        c.circle(cx + sx * s * 0.35, cy + s * 0.18, s * 0.1, stroke=1, fill=1)
    c.setFillColorRGB(0, 0, 0)
    c.circle(cx, cy - s * 0.12, s * 0.12, stroke=1, fill=1)
    c.setFillColorRGB(0, 0, 0)
    c.line(cx, cy - s * 0.24, cx, cy - s * 0.4)
    mouth = c.beginPath()
    mouth.moveTo(cx, cy - s * 0.4)
    mouth.curveTo(cx - s * 0.05, cy - s * 0.5, cx - s * 0.18, cy - s * 0.5, cx - s * 0.22, cy - s * 0.42)
    mouth.moveTo(cx, cy - s * 0.4)
    mouth.curveTo(cx + s * 0.05, cy - s * 0.5, cx + s * 0.18, cy - s * 0.5, cx + s * 0.22, cy - s * 0.42)
    c.drawPath(mouth, stroke=1, fill=0)


def draw_fish(c, cx, cy, s, lw=1.5):
    """Little fish with tail, scales and bubbles."""
    _setup(c, lw)
    c.ellipse(cx - s, cy - s * 0.6, cx + s * 0.6, cy + s * 0.6, stroke=1, fill=0)
    tail = c.beginPath()
    tail.moveTo(cx + s * 0.55, cy)
    tail.lineTo(cx + s * 1.1, cy + s * 0.5)
    tail.lineTo(cx + s * 1.1, cy - s * 0.5)
    tail.close()
    c.drawPath(tail, stroke=1, fill=0)
    c.circle(cx - s * 0.5, cy + s * 0.12, s * 0.12, stroke=1, fill=1)
    c.setFillColorRGB(0, 0, 0)
    for k in range(3):
        c.arc(cx - s * 0.4 + k * s * 0.35, cy - s * 0.35,
              cx + s * 0.0 + k * s * 0.35, cy + s * 0.35, 90, 180)
    c.circle(cx - s * 1.25, cy + s * 0.4, s * 0.1, stroke=1, fill=0)
    c.circle(cx - s * 1.45, cy + s * 0.7, s * 0.07, stroke=1, fill=0)


def draw_mushroom(c, cx, cy, s, lw=1.5):
    """Toadstool with a spotted cap."""
    _setup(c, lw)
    cap = c.beginPath()
    cap.moveTo(cx - s, cy)
    cap.arcTo(cx - s, cy - s * 0.2, cx + s, cy + s * 1.4, 0, 180)
    cap.lineTo(cx + s, cy)
    cap.close()
    c.drawPath(cap, stroke=1, fill=0)
    c.line(cx - s, cy, cx + s, cy)
    c.rect(cx - s * 0.35, cy - s * 0.9, s * 0.7, s * 0.9, stroke=1, fill=0)
    for (dx, dy, rr) in [(-0.4, 0.5, 0.16), (0.35, 0.7, 0.13), (0.1, 0.35, 0.11)]:
        c.circle(cx + dx * s, cy + dy * s, rr * s, stroke=1, fill=0)


def draw_balloon(c, cx, cy, s, lw=1.5):
    """Party balloon with a curly string."""
    _setup(c, lw)
    c.ellipse(cx - s * 0.7, cy - s * 0.6, cx + s * 0.7, cy + s, stroke=1, fill=0)
    knot = c.beginPath()
    knot.moveTo(cx - s * 0.12, cy - s * 0.6)
    knot.lineTo(cx + s * 0.12, cy - s * 0.6)
    knot.lineTo(cx, cy - s * 0.78)
    knot.close()
    c.drawPath(knot, stroke=1, fill=0)
    string = c.beginPath()
    string.moveTo(cx, cy - s * 0.78)
    string.curveTo(cx + s * 0.3, cy - s * 1.3, cx - s * 0.3, cy - s * 1.7, cx, cy - s * 2.2)
    c.drawPath(string, stroke=1, fill=0)


# Name -> drawing function, used by themes and openings.
ICONS = {
    "unicorn": draw_unicorn, "castle": draw_castle, "cat": draw_cat,
    "bunny": draw_bunny, "butterfly": draw_butterfly, "flower": draw_flower,
    "fish": draw_fish, "mushroom": draw_mushroom, "balloon": draw_balloon,
    "crown": draw_crown, "rainbow": draw_rainbow, "cloud": draw_cloud,
    "star": draw_star, "heart": draw_heart,
}


def draw_arrow(c, x1, y1, x2, y2, lw):
    """Draw an arrow from (x1, y1) to (x2, y2)."""
    c.setLineWidth(max(lw, 2.2))
    c.setLineCap(1)
    c.line(x1, y1, x2, y2)
    ang = math.atan2(y2 - y1, x2 - x1)
    for da in (math.radians(150), math.radians(-150)):
        c.line(x2, y2, x2 + 7 * math.cos(ang + da), y2 + 7 * math.sin(ang + da))


def arrow_for_opening(point, into):
    """Arrow segment for an opening point (px, py, edge)."""
    px, py, edge = point
    if edge == "top":
        return (px, py + 24, px, py + 6) if into else (px, py + 6, px, py + 24)
    if edge == "bottom":
        return (px, py - 24, px, py - 6) if into else (px, py - 6, px, py - 24)
    if edge == "left":
        return (px - 24, py, px - 6, py) if into else (px - 6, py, px - 24, py)
    return (px + 24, py, px + 6, py) if into else (px + 6, py, px + 24, py)


def icon_extents(icon_name, size):
    """Conservative icon extents from center: (left, right, down, up)."""
    # Most drawings stay within ~1.1*size; bunny/balloon tails reach ~2.2*size.
    if icon_name in {"bunny", "balloon"}:
        r = 2.3 * size
        return r, r, r, r
    r = 1.5 * size
    return r, r, r, r


def icon_collision_radius(icon_name, size):
    """Circle radius enclosing the icon drawing."""
    left, right, down, up = icon_extents(icon_name, size)
    return max(left, right, down, up)


def _clamp(v, lo, hi):
    return max(lo, min(hi, v))


def _point_to_segment_distance(px, py, x1, y1, x2, y2):
    dx, dy = x2 - x1, y2 - y1
    if dx == 0 and dy == 0:
        return math.hypot(px - x1, py - y1)
    t = ((px - x1) * dx + (py - y1) * dy) / float(dx * dx + dy * dy)
    t = max(0.0, min(1.0, t))
    qx, qy = x1 + t * dx, y1 + t * dy
    return math.hypot(px - qx, py - qy)


def _rect_for_center(cx, baseline_y, text, font_size):
    """Approximate text rectangle (x0, y0, x1, y1) from center + baseline."""
    # Wider estimate for CJK scripts (roughly square glyph cells).
    has_non_latin = any(ord(ch) > 127 for ch in text)
    per_char = 1.0 if has_non_latin else 0.56
    width = max(1.0, per_char * font_size * len(text))
    ascent = 0.85 * font_size
    descent = 0.25 * font_size
    x0 = cx - width / 2.0
    x1 = cx + width / 2.0
    y0 = baseline_y - descent
    y1 = baseline_y + ascent
    return x0, y0, x1, y1


def _rect_segment_distance(rect, seg):
    """Distance between an axis-aligned rect and axis-aligned segment."""
    rx0, ry0, rx1, ry1 = rect
    x1, y1, x2, y2 = seg
    if abs(x1 - x2) < 1e-9:  # vertical
        x = x1
        sy0, sy1 = sorted((y1, y2))
        overlap_y = not (sy1 < ry0 or sy0 > ry1)
        if overlap_y and rx0 <= x <= rx1:
            return 0.0
        dx = 0.0 if rx0 <= x <= rx1 else min(abs(x - rx0), abs(x - rx1))
        if overlap_y:
            dy = 0.0
        else:
            dy = min(abs(sy0 - ry1), abs(ry0 - sy1))
        return math.hypot(dx, dy)
    # horizontal
    y = y1
    sx0, sx1 = sorted((x1, x2))
    overlap_x = not (sx1 < rx0 or sx0 > rx1)
    if overlap_x and ry0 <= y <= ry1:
        return 0.0
    dy = 0.0 if ry0 <= y <= ry1 else min(abs(y - ry0), abs(y - ry1))
    if overlap_x:
        dx = 0.0
    else:
        dx = min(abs(sx0 - rx1), abs(rx0 - sx1))
    return math.hypot(dx, dy)


def _rects_overlap(a, b):
    ax0, ay0, ax1, ay1 = a
    bx0, by0, bx1, by1 = b
    return not (ax1 < bx0 or bx1 < ax0 or ay1 < by0 or by1 < ay0)


def _point_to_point_distance(x1, y1, x2, y2):
    return math.hypot(x2 - x1, y2 - y1)


def _point_to_rect_distance(px, py, rect):
    """Distance from point to axis-aligned rectangle (0 if inside)."""
    x0, y0, x1, y1 = rect
    if x0 <= px <= x1 and y0 <= py <= y1:
        return 0.0
    dx = 0.0 if x0 <= px <= x1 else min(abs(px - x0), abs(px - x1))
    dy = 0.0 if y0 <= py <= y1 else min(abs(py - y0), abs(py - y1))
    return math.hypot(dx, dy)


def label_placement_for_opening(point, icon_center, icon_name, size, label,
                                label_size=7.5, page_margin=6.0):
    """Choose label position guaranteed not to overlap arrow/icon/maze/page."""
    ix, iy = icon_center
    px, py, edge = point
    left, right, down, up = icon_extents(icon_name, size)
    icon_rect = (ix - left, iy - down, ix + right, iy + up)
    arrow = arrow_for_opening(point, edge in {"top", "left"})

    # Candidate baselines ordered by preference.
    if edge == "top":
        candidates = [(ix, iy + up + 8), (ix, iy - down - 12)]
    elif edge == "bottom":
        candidates = [(ix, iy - down - 12), (ix, iy + up + 8)]
    elif edge == "left":
        candidates = [(ix, iy + up + 8), (ix, iy - down - 14), (ix + right + 10, iy)]
    else:  # right
        candidates = [(ix, iy + up + 8), (ix, iy - down - 14), (ix - left - 10, iy)]

    maze_rect = (MAZE_X0, MAZE_Y0, MAZE_X0 + MAZE_SIDE, MAZE_Y0 + MAZE_SIDE)
    clearance = 3.0
    for cx, by in candidates:
        rect = _rect_for_center(cx, by, label, label_size)
        # Keep in page.
        dx = 0.0
        dy = 0.0
        if rect[0] < page_margin:
            dx = page_margin - rect[0]
        elif rect[2] > PAGE_W - page_margin:
            dx = (PAGE_W - page_margin) - rect[2]
        if rect[1] < page_margin:
            dy = page_margin - rect[1]
        elif rect[3] > PAGE_H - page_margin:
            dy = (PAGE_H - page_margin) - rect[3]
        cx += dx
        by += dy
        rect = _rect_for_center(cx, by, label, label_size)

        if _rects_overlap(rect, icon_rect):
            continue
        if _rects_overlap(rect, maze_rect):
            continue
        if _rect_segment_distance(rect, arrow) < clearance:
            continue
        return cx, by

    # Last-resort clamped fallback above icon.
    cx, by = ix, iy + up + 8
    rect = _rect_for_center(cx, by, label, label_size)
    if rect[0] < page_margin:
        cx += page_margin - rect[0]
    elif rect[2] > PAGE_W - page_margin:
        cx -= rect[2] - (PAGE_W - page_margin)
    rect = _rect_for_center(cx, by, label, label_size)
    if rect[1] < page_margin:
        by += page_margin - rect[1]
    elif rect[3] > PAGE_H - page_margin:
        by -= rect[3] - (PAGE_H - page_margin)
    return cx, by


def icon_center_for_opening(point, icon_name, size):
    """Place icon center outside arrow and fully inside page bounds."""
    px, py, edge = point
    page_margin = 8.0
    clearance = 8.0
    radius = icon_collision_radius(icon_name, size)

    # Desired offset along outward normal from opening.
    dist = 24 + radius + clearance
    if edge == "top":
        ix, iy = px, py + dist
    elif edge == "bottom":
        ix, iy = px, py - dist
    elif edge == "left":
        ix, iy = px - dist, py
    else:
        ix, iy = px + dist, py

    left, right, down, up = icon_extents(icon_name, size)

    # Keep full icon inside page.
    ix = _clamp(ix, page_margin + left, PAGE_W - page_margin - right)
    iy = _clamp(iy, page_margin + down, PAGE_H - page_margin - up)

    # If clamping brought icon too close to arrow, push away orthogonally.
    x1, y1, x2, y2 = arrow_for_opening(point, edge in {"top", "left"})
    need = radius + clearance
    for _ in range(5):
        d = _point_to_segment_distance(ix, iy, x1, y1, x2, y2)
        if d >= need:
            break
        shift = need - d + 1.0
        if edge in {"top", "bottom"}:
            # Vertical arrow -> move icon sideways.
            cand1 = (_clamp(ix + shift, page_margin + left, PAGE_W - page_margin - right), iy)
            cand2 = (_clamp(ix - shift, page_margin + left, PAGE_W - page_margin - right), iy)
        else:
            # Horizontal arrow -> move icon up/down.
            cand1 = (ix, _clamp(iy + shift, page_margin + down, PAGE_H - page_margin - up))
            cand2 = (ix, _clamp(iy - shift, page_margin + down, PAGE_H - page_margin - up))
        d1 = _point_to_segment_distance(cand1[0], cand1[1], x1, y1, x2, y2)
        d2 = _point_to_segment_distance(cand2[0], cand2[1], x1, y1, x2, y2)
        ix, iy = cand1 if d1 >= d2 else cand2

    return ix, iy


def draw_maze(c, x0, y0, side, cols, rows, right, down, lw, entrance, exit_):
    """Render the maze grid plus the entrance/exit openings and arrows.

    Returns the two opening points (px, py, edge) so the caller can place the
    themed icons and labels just outside the maze.
    """
    cw, ch = side / cols, side / rows
    c.setStrokeColorRGB(0, 0, 0)
    c.setLineWidth(lw)
    c.setLineCap(1)
    c.setLineJoin(1)

    def gx(col):
        return x0 + col * cw

    def gy(row):  # top edge of grid row `row`
        return y0 + side - row * ch

    # Internal walls: a wall exists wherever a passage is NOT open.
    for r in range(rows):
        for col in range(cols - 1):
            if not right[r][col]:
                xx = gx(col + 1)
                c.line(xx, gy(r), xx, gy(r + 1))
    for r in range(rows - 1):
        for col in range(cols):
            if not down[r][col]:
                yy = gy(r + 1)
                c.line(gx(col), yy, gx(col + 1), yy)

    top, bottom = gy(0), gy(rows)
    left, right_x = gx(0), gx(cols)
    skip = {entrance, exit_}

    # Outer border drawn segment by segment, leaving gaps at the openings.
    for col in range(cols):
        if ("top", col) not in skip:
            c.line(gx(col), top, gx(col + 1), top)
        if ("bottom", col) not in skip:
            c.line(gx(col), bottom, gx(col + 1), bottom)
    for r in range(rows):
        if ("left", r) not in skip:
            c.line(left, gy(r), left, gy(r + 1))
        if ("right", r) not in skip:
            c.line(right_x, gy(r), right_x, gy(r + 1))

    def opening_point(spec):
        edge, idx = spec
        if edge == "top":
            return gx(idx) + cw / 2, top, "top"
        if edge == "bottom":
            return gx(idx) + cw / 2, bottom, "bottom"
        if edge == "left":
            return left, gy(idx) - ch / 2, "left"
        return right_x, gy(idx) - ch / 2, "right"

    ep = opening_point(entrance)
    xp = opening_point(exit_)

    draw_arrow(c, *arrow_for_opening(ep, into=True), lw)
    draw_arrow(c, *arrow_for_opening(xp, into=False), lw)
    return ep, xp


def centered_text(c, x, y, text, font, size):
    """Draw `text` horizontally centred on `x` at baseline `y`."""
    from reportlab.pdfbase.pdfmetrics import stringWidth  # lazy: keeps logic import-safe
    c.setFont(font, size)
    c.setFillColorRGB(0, 0, 0)
    c.drawString(x - stringWidth(text, font, size) / 2, y, text)


def place_icon_and_label(c, point, icon_name, label, size, label_font="Helvetica-Bold"):
    """Place a themed icon and its label just outside the given opening."""
    px, py, edge = point
    icon = ICONS[icon_name]
    ix, iy = icon_center_for_opening(point, icon_name, size)
    lx, ly = label_placement_for_opening(point, (ix, iy), icon_name, size, label, 7.5)
    label_rect = _rect_for_center(lx, ly, label, 7.5)
    icon_radius = icon_collision_radius(icon_name, size)
    icon(c, ix, iy, size)
    centered_text(c, lx, ly, label, label_font, 7.5)
    return {
        "icon_center": (ix, iy),
        "icon_radius": icon_radius,
        "label_rect": label_rect,
    }


def _motif_conflicts(mx, my, radius, ep, xp, protected_circles=(), protected_rects=()):
    """True if motif would overlap arrows/openings or protected geometry."""
    clearance = 3.0
    arrows = (arrow_for_opening(ep, True), arrow_for_opening(xp, False))
    for seg in arrows:
        if _point_to_segment_distance(mx, my, *seg) < radius + clearance:
            return True
    # Also keep clear of opening points themselves.
    if _point_to_point_distance(mx, my, ep[0], ep[1]) < radius + 12:
        return True
    if _point_to_point_distance(mx, my, xp[0], xp[1]) < radius + 12:
        return True
    for cx, cy, cr in protected_circles:
        if _point_to_point_distance(mx, my, cx, cy) < radius + cr + clearance:
            return True
    for rect in protected_rects:
        if _point_to_rect_distance(mx, my, rect) < radius + clearance:
            return True
    return False


def draw_page(c, page_idx, total, n, rng, min_path_factor=MIN_PATH_FACTOR,
              localization=None, seed=None):
    """Render one full maze page (title, difficulty stars, maze, decorations)."""
    cw = MAZE_SIDE / n
    lw = max(1.8, min(3.4, cw * 0.075))  # wall thickness scales with cell size

    # Place the entrance/exit at the farthest-apart border cells and re-carve
    # until the forced route is long (>= min_path_factor * n*n cells), so the
    # solution can never be a trivially short hop between nearby openings.
    right, down, entrance, exit_, _ = generate_long_maze(
        n, rng, min_path_factor=min_path_factor)

    loc = localization or LOCALIZATIONS[DEFAULT_LOCALE]
    title_font = loc.get("title_font", "Helvetica-Bold")
    label_font = loc.get("label_font", "Helvetica-Bold")
    footer_font = loc.get("footer_font", "Helvetica")

    # Pick a coherent random theme; emphasise the last page.
    start_icon, goal_icon, title = rng.choice(loc["theme_pool"])
    if page_idx == total - 1:
        title = loc["last_page_prefix"] + title[0].lower() + title[1:]

    title_y = min(PAGE_H - 42, MAZE_TOP + 152)
    centered_text(c, PAGE_W / 2, title_y, title, title_font, 16)

    # Difficulty stars: relative progress through the booklet (1..5).
    filled = 1 + int((page_idx / max(1, total - 1)) * 4 + 0.5)
    star_x0 = PAGE_W / 2 - (5 * 16) / 2 + 8
    star_y = title_y - 24
    for i in range(5):
        draw_star(c, star_x0 + i * 16, star_y, 6, lw=1.0, fill=(i < filled))

    ep, xp = draw_maze(c, MAZE_X0, MAZE_Y0, MAZE_SIDE, n, n,
                       right, down, lw, entrance, exit_)
    start_layout = place_icon_and_label(c, ep, start_icon, loc["start_label"], 17, label_font)
    goal_layout = place_icon_and_label(c, xp, goal_icon, loc["goal_label"], 19, label_font)
    protected_circles = [
        (*start_layout["icon_center"], start_layout["icon_radius"]),
        (*goal_layout["icon_center"], goal_layout["icon_radius"]),
    ]
    protected_rects = [start_layout["label_rect"], goal_layout["label_rect"]]

    # Corner decorations (kept off the edges, where the openings can be).
    deco_rng = random.Random(rng.random())
    corner_fns = {"cloud": draw_cloud, "flower": draw_flower,
                  "heart": draw_heart, "star": draw_star}
    for (mx, my) in [(MAZE_X0 - 30, MAZE_TOP + 6),
                     (PAGE_W - (MAZE_X0 - 30), MAZE_TOP + 6),
                     (MAZE_X0 - 30, MAZE_Y0 - 6),
                     (PAGE_W - (MAZE_X0 - 30), MAZE_Y0 - 6)]:
        motif = deco_rng.choice(MARGIN_MOTIFS)
        motif_size = deco_rng.uniform(7, 10)
        if _motif_conflicts(mx, my, motif_size + 3, ep, xp, protected_circles, protected_rects):
            continue
        corner_fns[motif](c, mx, my, motif_size, lw=1.1)

    # Bottom decorative strip.
    strip_y = MAZE_Y0 - 22
    for i in range(7):
        bx = MAZE_X0 + 20 + i * (MAZE_SIDE - 40) / 6
        motif = MARGIN_MOTIFS[i % len(MARGIN_MOTIFS)]
        motif_size = 7
        if _motif_conflicts(bx, strip_y, motif_size + 3, ep, xp, protected_circles, protected_rects):
            # One-shot local shift away from arrows before drawing.
            alt_bx = bx - 18 if bx > PAGE_W / 2 else bx + 18
            if not _motif_conflicts(alt_bx, strip_y, motif_size + 3, ep, xp, protected_circles, protected_rects):
                bx = alt_bx
            else:
                continue
        corner_fns[motif](c, bx, strip_y, motif_size, lw=1.0)

    # Footer.
    c.setFont(footer_font, 9)
    c.setFillColorRGB(0.25, 0.25, 0.25)
    centered_text(c, PAGE_W / 2, 15, loc["page_label"].format(page_idx + 1, total),
                  footer_font, 9)
    if seed is not None:
        # Small, unobtrusive seed reference so a booklet can be reprinted identically.
        c.setFont(footer_font, 6.5)
        c.setFillColorRGB(0.55, 0.55, 0.55)
        c.drawRightString(PAGE_W - MAZE_X0, 15, "Seed: {}".format(seed))
    c.setFillColorRGB(0, 0, 0)


def build(path, pages, master_seed, difficulty, min_path_factor=MIN_PATH_FACTOR,
          locale=DEFAULT_LOCALE):
    """Build the whole PDF and return the list of per-page grid sizes."""
    try:
        from reportlab.pdfgen import canvas  # lazy: only needed for rendering
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.cidfonts import UnicodeCIDFont
        from reportlab.pdfbase.ttfonts import TTFont
    except ImportError:
        sys.exit("reportlab is required to build the PDF. "
                 "Run with 'uv run generate_mazes.py' or 'pip install reportlab'.")

    rng = random.Random(master_seed)
    loc = get_localization(locale)
    _register_locale_fonts(loc, pdfmetrics, UnicodeCIDFont, TTFont)

    output_dir = os.path.dirname(path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    sizes = grid_sizes(pages, difficulty)
    c = canvas.Canvas(path, pagesize=(PAGE_W, PAGE_H), invariant=1)
    c.setTitle(loc["pdf_title"])
    for i in range(pages):
        draw_page(c, i, pages, sizes[i], rng, min_path_factor, loc, seed=master_seed)
        c.showPage()
    c.save()
    return sizes


@dataclass(frozen=True)
class GenerationOptions:
    """Public options for a generation run."""

    output: str = "output/mazes.pdf"
    pages: int = 20
    difficulty: float = DEFAULT_DIFFICULTY
    seed: Optional[int] = None
    min_path_factor: float = MIN_PATH_FACTOR
    locale: str = DEFAULT_LOCALE


def run_generation(opts: GenerationOptions):
    """Run one generation job and return `(seed_used, sizes)`."""
    if opts.pages < 1:
        raise ValueError("pages must be >= 1")
    if not MIN_DIFFICULTY <= opts.difficulty <= MAX_DIFFICULTY:
        raise ValueError(
            f"difficulty must be in [{MIN_DIFFICULTY:g}, {MAX_DIFFICULTY:g}]"
        )
    if not 0.0 < opts.min_path_factor <= 1.0:
        raise ValueError("min_path_factor must be in (0, 1]")
    if opts.locale not in LOCALIZATIONS:
        raise ValueError(
            "unknown locale %r (supported: %s)"
            % (opts.locale, ", ".join(sorted(LOCALIZATIONS)))
        )

    seed = opts.seed if opts.seed is not None else int.from_bytes(os.urandom(8), "big")
    sizes = build(
        opts.output,
        opts.pages,
        seed,
        opts.difficulty,
        opts.min_path_factor,
        opts.locale,
    )
    return seed, sizes


def main(argv=None):
    """Backward-compatible entrypoint; delegates CLI parsing to cli.py."""
    from .cli import main as cli_main

    return cli_main(argv)


if __name__ == "__main__":
    main()
