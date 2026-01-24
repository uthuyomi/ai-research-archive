import rawCharacters from "./characters.json";

/**
 * キャラクター定義（UI + world）
 * ================================
 * このファイルが「唯一の入口（SSOT）」。
 *
 * ・UI 表示
 * ・人格（プロンプト）
 * ・どの世界 / ロケーションに存在するか
 *
 * すべての判断はここから派生させる。
 */
export const CHARACTERS = rawCharacters as Record<
  string,
  {
    id: string;
    name: string;
    title: string;
    world?: {
      map: string; // gensokyo / deep / higan など
      location: string; // scarlet_mansion / chireiden など
    };
    color: {
      accent: string;
    };
    ui: {
      chatBackground: string;
      placeholder: string;
    };
  }
>;

/* =========================================================
 * 以下は「派生セレクタ」
 * 👉 データは増やさず、見方だけを定義する
 * ========================================================= */

/**
 * 指定されたロケーションに「現在存在するキャラクター一覧」を返す
 *
 * - characters.json に存在するキャラのみ対象
 * - 未実装キャラは自動的に除外される
 * - グループチャット / イベント判定の基礎になる
 */
export function getCharactersByLocation(map: string, locationId: string) {
  return Object.values(CHARACTERS).filter(
    (ch) => ch.world?.map === map && ch.world?.location === locationId
  );
}

/**
 * グループチャットが有効かどうかの判定
 *
 * - 同一ロケーションに 2 人以上いれば true
 * - UI 側ではこれを見て「個別 / グループ」切替を出す
 */
export function canEnableGroupChat(map: string, locationId: string): boolean {
  return getCharactersByLocation(map, locationId).length >= 2;
}

/**
 * 将来用：
 * イベント用に「参加キャラ候補」を取得
 *
 * 例：
 * - 博麗神社・宴会モード
 * - 紅魔館・夜会モード
 *
 * ※ 今は単なる alias だが、
 *   フィルタ条件を足せばイベント制御にそのまま使える
 */
export function getGroupChatCandidates(map: string, locationId: string) {
  return getCharactersByLocation(map, locationId);
}
