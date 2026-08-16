// ガチャで集められるどうぶつカード(8種)
// svg は 0 0 100 100 のミニイラスト。英語の名前を覚えるおまけつき
const CARDS = [
  {
    id: "lion", nameEn: "Lion", nameJa: "らいおん",
    svg: `<circle cx="50" cy="52" r="34" fill="#e8a33d"/>
      <circle cx="50" cy="52" r="24" fill="#ffd98e"/>
      <circle cx="42" cy="48" r="3.5" fill="#4a3728"/><circle cx="58" cy="48" r="3.5" fill="#4a3728"/>
      <ellipse cx="50" cy="57" rx="4" ry="3" fill="#b3541e"/>
      <path d="M44 63 Q50 68 56 63" fill="none" stroke="#4a3728" stroke-width="2.5" stroke-linecap="round"/>`
  },
  {
    id: "panda", nameEn: "Panda", nameJa: "ぱんだ",
    svg: `<circle cx="28" cy="30" r="12" fill="#3a3a3a"/><circle cx="72" cy="30" r="12" fill="#3a3a3a"/>
      <circle cx="50" cy="54" r="30" fill="#fff" stroke="#ddd" stroke-width="2"/>
      <ellipse cx="39" cy="50" rx="8" ry="10" fill="#3a3a3a" transform="rotate(-15 39 50)"/>
      <ellipse cx="61" cy="50" rx="8" ry="10" fill="#3a3a3a" transform="rotate(15 61 50)"/>
      <circle cx="40" cy="50" r="3" fill="#fff"/><circle cx="60" cy="50" r="3" fill="#fff"/>
      <ellipse cx="50" cy="62" rx="4" ry="3" fill="#3a3a3a"/>
      <path d="M45 68 Q50 72 55 68" fill="none" stroke="#3a3a3a" stroke-width="2.5" stroke-linecap="round"/>`
  },
  {
    id: "penguin", nameEn: "Penguin", nameJa: "ぺんぎん",
    svg: `<ellipse cx="50" cy="55" rx="30" ry="36" fill="#3d5a73"/>
      <ellipse cx="50" cy="62" rx="20" ry="26" fill="#fff"/>
      <circle cx="42" cy="42" r="4" fill="#fff"/><circle cx="58" cy="42" r="4" fill="#fff"/>
      <circle cx="42" cy="42" r="2" fill="#26384a"/><circle cx="58" cy="42" r="2" fill="#26384a"/>
      <polygon points="44,50 56,50 50,58" fill="#f7941d"/>
      <ellipse cx="38" cy="90" rx="9" ry="4" fill="#f7941d"/><ellipse cx="62" cy="90" rx="9" ry="4" fill="#f7941d"/>`
  },
  {
    id: "rabbit", nameEn: "Rabbit", nameJa: "うさぎ",
    svg: `<ellipse cx="38" cy="24" rx="8" ry="20" fill="#fff" stroke="#eee" stroke-width="2"/>
      <ellipse cx="62" cy="24" rx="8" ry="20" fill="#fff" stroke="#eee" stroke-width="2"/>
      <ellipse cx="38" cy="24" rx="4" ry="13" fill="#ffc9d6"/><ellipse cx="62" cy="24" rx="4" ry="13" fill="#ffc9d6"/>
      <circle cx="50" cy="58" r="28" fill="#fff" stroke="#eee" stroke-width="2"/>
      <circle cx="42" cy="54" r="3.5" fill="#4a3728"/><circle cx="58" cy="54" r="3.5" fill="#4a3728"/>
      <ellipse cx="50" cy="63" rx="3.5" ry="2.5" fill="#f06292"/>
      <path d="M50 65 Q50 71 44 72 M50 65 Q50 71 56 72" fill="none" stroke="#4a3728" stroke-width="2" stroke-linecap="round"/>
      <circle cx="35" cy="62" r="5" fill="#ffc9d6" opacity="0.8"/><circle cx="65" cy="62" r="5" fill="#ffc9d6" opacity="0.8"/>`
  },
  {
    id: "elephant", nameEn: "Elephant", nameJa: "ぞう",
    svg: `<circle cx="26" cy="52" r="16" fill="#9fb7cc"/><circle cx="74" cy="52" r="16" fill="#9fb7cc"/>
      <circle cx="50" cy="52" r="27" fill="#b7cadb"/>
      <circle cx="42" cy="46" r="3.5" fill="#4a3728"/><circle cx="58" cy="46" r="3.5" fill="#4a3728"/>
      <path d="M50 56 Q52 70 62 76 Q66 78 66 73 Q60 68 58 58" fill="#b7cadb" stroke="#9fb7cc" stroke-width="2"/>
      <circle cx="40" cy="56" r="5" fill="#ffc9d6" opacity="0.6"/><circle cx="60" cy="56" r="5" fill="#ffc9d6" opacity="0.6"/>`
  },
  {
    id: "fox", nameEn: "Fox", nameJa: "きつね",
    svg: `<polygon points="24,18 44,34 26,44" fill="#e88b3a"/><polygon points="76,18 56,34 74,44" fill="#e88b3a"/>
      <polygon points="28,23 41,34 30,40" fill="#fff"/><polygon points="72,23 59,34 70,40" fill="#fff"/>
      <circle cx="50" cy="56" r="28" fill="#e88b3a"/>
      <path d="M30 66 Q50 88 70 66 Q60 78 50 78 Q40 78 30 66" fill="#fff"/>
      <circle cx="41" cy="52" r="3.5" fill="#4a3728"/><circle cx="59" cy="52" r="3.5" fill="#4a3728"/>
      <ellipse cx="50" cy="66" rx="4" ry="3" fill="#4a3728"/>`
  },
  {
    id: "owl", nameEn: "Owl", nameJa: "ふくろう",
    svg: `<polygon points="28,22 38,32 22,34" fill="#8d6e4f"/><polygon points="72,22 62,32 78,34" fill="#8d6e4f"/>
      <ellipse cx="50" cy="56" rx="30" ry="32" fill="#a5876a"/>
      <circle cx="40" cy="48" r="11" fill="#fff"/><circle cx="60" cy="48" r="11" fill="#fff"/>
      <circle cx="40" cy="48" r="5" fill="#4a3728"/><circle cx="60" cy="48" r="5" fill="#4a3728"/>
      <polygon points="46,58 54,58 50,66" fill="#f7941d"/>
      <path d="M36 72 Q42 78 48 72 M52 72 Q58 78 64 72" fill="none" stroke="#8d6e4f" stroke-width="2.5" stroke-linecap="round"/>`
  },
  {
    id: "turtle", nameEn: "Turtle", nameJa: "かめ",
    svg: `<ellipse cx="50" cy="58" rx="30" ry="24" fill="#6aa84f"/>
      <path d="M35 45 L50 38 L65 45 L68 60 L58 72 L42 72 L32 60 Z" fill="#4d8138" opacity="0.5"/>
      <circle cx="80" cy="46" r="11" fill="#8fd08a"/>
      <circle cx="83" cy="43" r="2.5" fill="#4a3728"/>
      <path d="M80 50 Q84 52 87 50" fill="none" stroke="#2f6e35" stroke-width="2" stroke-linecap="round"/>
      <ellipse cx="32" cy="80" rx="8" ry="5" fill="#8fd08a"/><ellipse cx="62" cy="82" rx="8" ry="5" fill="#8fd08a"/>`
  }
];

const GACHA_COST = 3; // ガチャ1回に必要なコイン

function cardSvgHtml(card, size) {
  return `<svg viewBox="0 0 100 100" width="${size}" height="${size}">${card.svg}</svg>`;
}
