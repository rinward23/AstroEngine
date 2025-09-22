"""I Ching hexagram correspondences using the King Wen sequence."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

__all__ = ["Hexagram", "I_CHING_HEXAGRAMS"]


@dataclass(frozen=True)
class Hexagram:
    """Representation of a single I Ching hexagram."""

    number: int
    chinese: str
    pinyin: str
    translation: str
    keywords: Tuple[str, ...]

    def to_payload(self) -> dict[str, object]:
        return {
            "number": self.number,
            "chinese": self.chinese,
            "pinyin": self.pinyin,
            "translation": self.translation,
            "keywords": list(self.keywords),
        }


I_CHING_HEXAGRAMS: Tuple[Hexagram, ...] = (
    Hexagram(1, "乾", "Qián", "The Creative", ("initiative", "yang", "heaven")),
    Hexagram(2, "坤", "Kūn", "The Receptive", ("yielding", "earth", "nurture")),
    Hexagram(3, "屯", "Zhūn", "Difficulty at the Beginning", ("birth", "trial", "endurance")),
    Hexagram(4, "蒙", "Méng", "Youthful Folly", ("learning", "guidance", "correcting")),
    Hexagram(5, "需", "Xū", "Waiting", ("patience", "timing", "trust")),
    Hexagram(6, "訟", "Sòng", "Conflict", ("dispute", "truth", "judgement")),
    Hexagram(7, "師", "Shī", "The Army", ("discipline", "organization", "collective action")),
    Hexagram(8, "比", "Bǐ", "Holding Together", ("union", "fellowship", "commitment")),
    Hexagram(9, "小畜", "Xiǎo Chù", "Taming Power of the Small", ("gentle influence", "preparation", "incremental gain")),
    Hexagram(10, "履", "Lǚ", "Treading", ("conduct", "sensitivity", "respect")),
    Hexagram(11, "泰", "Tài", "Peace", ("harmony", "prosperity", "alignment")),
    Hexagram(12, "否", "Pǐ", "Standstill", ("blockage", "stagnation", "disengage")),
    Hexagram(13, "同人", "Tóng Rén", "Fellowship with Men", ("community", "shared vision", "alliances")),
    Hexagram(14, "大有", "Dà Yǒu", "Possession in Great Measure", ("abundance", "nobility", "responsibility")),
    Hexagram(15, "謙", "Qiān", "Modesty", ("humility", "balance", "moderation")),
    Hexagram(16, "豫", "Yù", "Enthusiasm", ("motivation", "music", "mobilise")),
    Hexagram(17, "隨", "Suí", "Following", ("adaptation", "loyalty", "alignment")),
    Hexagram(18, "蠱", "Gǔ", "Work on the Decayed", ("remedy", "repair", "responsibility")),
    Hexagram(19, "臨", "Lín", "Approach", ("care", "oversight", "nurture")),
    Hexagram(20, "觀", "Guān", "Contemplation", ("reflection", "ritual", "overview")),
    Hexagram(21, "噬嗑", "Shì Kè", "Biting Through", ("decisiveness", "clarity", "justice")),
    Hexagram(22, "賁", "Bì", "Grace", ("beauty", "culture", "presentation")),
    Hexagram(23, "剝", "Bō", "Splitting Apart", ("decline", "simplify", "shed")),
    Hexagram(24, "復", "Fù", "Return", ("renewal", "cyclic flow", "turning point")),
    Hexagram(25, "無妄", "Wú Wàng", "Innocence", ("integrity", "unexpected", "truth")),
    Hexagram(26, "大畜", "Dà Chù", "Taming Power of the Great", ("restraint", "accumulation", "strength")),
    Hexagram(27, "頤", "Yí", "Nourishing", ("sustenance", "speech", "intake")),
    Hexagram(28, "大過", "Dà Guò", "Preponderance of the Great", ("strain", "responsibility", "support")),
    Hexagram(29, "坎", "Kǎn", "The Abysmal", ("danger", "depth", "perseverance")),
    Hexagram(30, "離", "Lí", "The Clinging", ("illumination", "clarity", "adhesion")),
    Hexagram(31, "咸", "Xián", "Influence", ("attraction", "affection", "resonance")),
    Hexagram(32, "恆", "Héng", "Duration", ("commitment", "endurance", "consistency")),
    Hexagram(33, "遯", "Dùn", "Retreat", ("withdrawal", "strategy", "self-preservation")),
    Hexagram(34, "大壯", "Dà Zhuàng", "Power of the Great", ("vital force", "momentum", "assertion")),
    Hexagram(35, "晉", "Jìn", "Progress", ("advancement", "recognition", "dawn")),
    Hexagram(36, "明夷", "Míng Yí", "Darkening of the Light", ("concealment", "injury", "guard inner fire")),
    Hexagram(37, "家人", "Jiā Rén", "The Family", ("roles", "home", "domestic harmony")),
    Hexagram(38, "睽", "Kuí", "Opposition", ("divergence", "individuality", "complementarity")),
    Hexagram(39, "蹇", "Jiǎn", "Obstruction", ("hindrance", "reflection", "pause")),
    Hexagram(40, "解", "Xiè", "Deliverance", ("release", "liberation", "relief")),
    Hexagram(41, "損", "Sǔn", "Decrease", ("sacrifice", "simplicity", "focus")),
    Hexagram(42, "益", "Yì", "Increase", ("abundance", "generosity", "momentum")),
    Hexagram(43, "夬", "Guài", "Breakthrough", ("resolution", "declaration", "decisive action")),
    Hexagram(44, "姤", "Gòu", "Coming to Meet", ("encounter", "temptation", "sudden contact")),
    Hexagram(45, "萃", "Cuì", "Gathering Together", ("assembly", "community", "celebration")),
    Hexagram(46, "升", "Shēng", "Pushing Upward", ("gradual advance", "effort", "aspiration")),
    Hexagram(47, "困", "Kùn", "Oppression", ("constraint", "exhaustion", "inner strength")),
    Hexagram(48, "井", "Jǐng", "The Well", ("resources", "depth", "renewal")),
    Hexagram(49, "革", "Gé", "Revolution", ("change", "molting", "radical shift")),
    Hexagram(50, "鼎", "Dǐng", "The Cauldron", ("transformation", "culture", "nourishment")),
    Hexagram(51, "震", "Zhèn", "The Arousing", ("shock", "awakening", "movement")),
    Hexagram(52, "艮", "Gèn", "Keeping Still", ("meditation", "stillness", "center")),
    Hexagram(53, "漸", "Jiàn", "Development", ("gradual progress", "fidelity", "evolution")),
    Hexagram(54, "歸妹", "Guī Mèi", "The Marrying Maiden", ("transition", "adaptation", "second place")),
    Hexagram(55, "豐", "Fēng", "Abundance", ("fullness", "visibility", "zenith")),
    Hexagram(56, "旅", "Lǚ", "The Wanderer", ("travel", "impermanence", "awareness")),
    Hexagram(57, "巽", "Xùn", "The Gentle", ("penetration", "wind", "permeation")),
    Hexagram(58, "兌", "Duì", "The Joyous", ("pleasure", "openness", "communication")),
    Hexagram(59, "渙", "Huàn", "Dispersion", ("dissolve barriers", "forgiveness", "release")),
    Hexagram(60, "節", "Jié", "Limitation", ("boundaries", "measure", "discipline")),
    Hexagram(61, "中孚", "Zhōng Fú", "Inner Truth", ("sincerity", "trust", "insight")),
    Hexagram(62, "小過", "Xiǎo Guò", "Preponderance of the Small", ("attention to detail", "caution", "modesty")),
    Hexagram(63, "既濟", "Jì Jì", "After Completion", ("culmination", "order", "maintenance")),
    Hexagram(64, "未濟", "Wèi Jì", "Before Completion", ("transition", "final steps", "alertness")),
)
