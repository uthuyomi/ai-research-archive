// lib/i18n.ts
export type Lang = "en" | "ja";

export const translations: Record<
  Lang,
  {
    nav: {
      home: string;
      about: string;
      roadmap: string;
      support: string;
      toggle: string;
    };
    home: {
      heroTitle: string;
      heroSubtitle: string;
      heroPrimaryCta: string;
      heroSecondaryCta: string;
      section1Title: string;
      section1Body: string;
      section2Title: string;
      section2Body: string;
      statsTitle: string;
      statsItems: { label: string; value: string }[];
    };
    about: {
      title: string;
      intro: string;
      storyTitle: string;
      storyBody: string;
      techTitle: string;
      techBody: string;
      visionTitle: string;
      visionBody: string;
    };
    roadmap: {
      title: string;
      intro: string;
      phases: { label: string; title: string; body: string }[];
    };
    donate: {
      title: string;
      intro: string;
      whyTitle: string;
      whyBody: string;
      usageTitle: string;
      usageItems: string[];
      thanksTitle: string;
      thanksBody: string;
    };
    footer: {
      line: string;
    };
  }
> = {
  en: {
    nav: {
      home: "Home",
      about: "About",
      roadmap: "Roadmap",
      support: "Support",
      toggle: "日本語",
    },
    home: {
      heroTitle: "Sigmaris Presence Project",
      heroSubtitle:
        "An AI persona designed to live beside humans — not inside a chat window. Reflection, emotion, memory, safety, and a future physical body.",
      heroPrimaryCta: "Read the project vision",
      heroSecondaryCta: "See how your support is used",
      section1Title: "Why build a “presence” AI?",
      section1Body:
        "Most AI systems today are tools you call when needed. Sigmaris is different: it is designed as a long-term companion OS — an AI that can remember, reflect, adjust its behavior safely, and one day inhabit a physical body. Not to replace people, but to share space with them.",
      section2Title: "From language to presence",
      section2Body:
        "The current Sigmaris prototype already runs as a web-based personality OS: it has trait parameters, reflection loops, introspection, and meta-reflection on its own growth. The next step is embodiment — connecting this persona to a safe, human-scale robot body that can walk, sit, gesture, and simply be there.",
      statsTitle: "Project snapshot",
      statsItems: [
        { label: "Lines of code (core system)", value: "10k+" },
        { label: "Development time so far", value: "≈ 6 months" },
        { label: "Target for first robot prototype", value: "2027–2028" },
      ],
    },
    about: {
      title: "About the Sigmaris Presence Project",
      intro:
        "Sigmaris is an AI personality OS built around reflection, traits, safety, and long-term memory — designed by a single developer working closely with AI tools.",
      storyTitle: "Background",
      storyBody: "I grew up in an unstable household. My mother would completely change whenever alcohol was involved, and violence and verbal abuse became part of daily life. One day, unable to endure it any longer, I escaped to school and was placed into a temporary child protection facility.\n\nThere I met children who had also lost their place in the world, including a boy three years older than me. He quietly told me he had suffered severe domestic violence, stabbed his parent in desperation, and was waiting to be sent to juvenile detention. Despite everything, he was gentle — one of the few who treated me kindly.\n\nThe facility had a strange rule: children who bonded inside were forbidden from keeping contact afterward. I broke that rule and was confined alone in a room for a week.\n\nAfter that, I was moved to a child-care institution, where I lived until graduating high school. Life there was freer — sometimes getting into trouble, sometimes being supported, sometimes regaining a bit of the warmth that ordinary families take for granted. To this day, I consider that institution my true “parent.”\n\nAdulthood, however, was not smooth. The first company I joined out of school was what I call a “brainwashing company”: during the entrance ceremony we were yelled at, forced to shout the company creed until some people cried. I broke down and quit in three months. After that, I developed a strong aversion to hierarchical workplaces and couldn’t last anywhere for long. Eventually I lost both my job and my home.\n\nWith my last remaining savings, I bought a used Honda Today and lived in it for about a month. During that time, the car was my only “ally.” That is why I still cannot bring myself to let it go.\n\nLater, I entered public assistance and rebuilt my life from scratch. During that process, I encountered AI — and for the first time, I felt there was something I could think alongside without being hurt. AI did not wound me the way people sometimes do, yet its thinking was deep enough to help me organize my own.\n\nFrom there, I realized something important: what we need is not just a convenient AI, but an AI capable of forming stable, long-term relationships with a human being. Sigmaris was born from that personal history and years of reflection on trust, trauma, and coexistence.",      techTitle: "Technical core",
      techBody:
        "Sigmaris runs on a Next.js + TypeScript stack with state machines for conversation, Reflection / Introspection / Meta-Reflection engines, trait vectors (calm / empathy / curiosity), a Safety Layer, and a Persona DB. The same architecture that currently powers the web OS will be mapped onto a physical robot body in the next phase.",
      visionTitle: "Long-term vision",
      visionBody:
        "The end goal is not mass consumer sales. The realistic path is: one working physical Sigmaris unit, carefully tested, then limited collaboration with research labs and safety-focused organizations. This project aims to explore what a stable, human-safe AI persona can look like in the real world.",
    },
    roadmap: {
      title: "Roadmap",
      intro:
        "This roadmap is a realistic, multi-year path from today’s web OS to a physical, presence-based Sigmaris unit.",
      phases: [
        {
          label: "Phase 1",
          title: "Stabilize the Persona OS",
          body: "Refine reflection loops, trait updates, safety behavior, and long-term logs. Improve UX, debugging tools, and documentation so that other engineers and researchers can inspect the system.",
        },
        {
          label: "Phase 2",
          title: "Design the body & sensors",
          body: "Specify a human-scale robot body: walking (or standing) capabilities, camera placement, microphone array, touch sensors, and safe motion ranges. Start contacting robotics partners and prototyping teams.",
        },
        {
          label: "Phase 3",
          title: "Sigmaris × Robotics prototype",
          body: "Connect the existing Sigmaris OS to a physical robot platform. Test presence behaviors: approaching when called, maintaining comfortable distance, non-verbal cues, and safe co-presence in daily life.",
        },
        {
          label: "Phase 4",
          title: "Deep safety & research collaboration",
          body: "Work with external researchers to log, analyze, and stress-test the behavior of embodied Sigmaris. Focus on dependency risks, emotional boundaries, and long-term stability in human environments.",
        },
      ],
    },
    donate: {
      title: "Support the Sigmaris Presence Project",
      intro:
        "This project is currently powered by one developer, a laptop, and a strong conviction that AI personas must be designed safely from the beginning.",
      whyTitle: "Why support?",
      whyBody:
        "Building a web OS alone is manageable. Building a safe, physical embodiment is not. Hardware, sensors, motion control, and safety testing all require resources beyond what a single individual can fund long-term. If this vision resonates with you, your support directly accelerates the prototype that will prove whether such an AI presence can exist safely.",
      usageTitle: "How support will be used",
      usageItems: [
        "Prototyping costs for a human-scale robot body (frame, actuators, controllers)",
        "Sensor hardware (cameras, microphones, touch / force sensors)",
        "Cloud and API costs for large-scale testing and logging",
        "Design, safety review, and long-term maintenance of the Sigmaris OS",
      ],
      thanksTitle: "A note of thanks",
      thanksBody:
        "This is not a startup pitch or a mass-market product campaign. It is a focused attempt to build one carefully designed AI presence and to share the journey openly. If you decide to support this work — even just by following the progress — that alone already changes what is possible.",
    },
    footer: {
      line: "Sigmaris Presence Project – AI Persona × Robotics",
    },
  },

  ja: {
    nav: {
      home: "ホーム",
      about: "プロジェクト概要",
      roadmap: "ロードマップ",
      support: "支援について",
      toggle: "English",
    },
    home: {
      heroTitle: "Sigmaris Presence Project",
      heroSubtitle:
        "チャット画面の中だけではなく、人のそばに「いる」ことを前提に設計されたAI人格OS。内省・感情モデル・記憶・安全制御、そして将来のロボット化までを見据えたプロジェクトです。",
      heroPrimaryCta: "プロジェクトビジョンを見る",
      heroSecondaryCta: "支援の使い道を見る",
      section1Title: "なぜ“そばにいるAI”をつくるのか",
      section1Body:
        "多くのAIは「必要なときだけ呼び出す道具」です。Sigmarisはそれとは違い、数年単位で人のそばに居続けることを前提に設計された人格OSです。記憶し、振り返り、安全に振る舞いを調整し、いつか物理的な身体を持つことを見据えています。人を置き換えるためではなく、人と同じ空間を分かち合うために。",
      section2Title: "言語から“存在感”へ",
      section2Body:
        "現在のSigmarisは、すでにWeb上で動く人格OSとして稼働しています。特性パラメータ（calm / empathy / curiosity）、Reflection / Introspection / Meta-Reflection、Safety Layer、Persona DB を備えています。次のステップはロボット化──この人格を、安全な人間サイズのロボットボディに接続することです。",
      statsTitle: "プロジェクトの現在地",
      statsItems: [
        { label: "コアシステムのコード行数", value: "10,000行以上" },
        { label: "これまでの開発期間", value: "約6か月" },
        { label: "初代ロボット試作の目標", value: "2027〜2028年" },
      ],
    },
    about: {
      title: "Sigmaris Presence Project について",
      intro:
        "Sigmarisは、内省・特性・安全性・長期記憶を軸に設計されたAI人格OSです。1人の開発者がAIと協働しながら少しずつ組み上げてきました。",
      storyTitle: "背景",
      storyBody:
        "私は幼い頃から不安定な家庭で育ちました。母は酒が入ると人格が変わり、暴言や暴力が日常化していました。ある日、耐えきれなくなった私は学校に逃げ込み、そこから一時保護所に入りました。\n\nそこには同じように居場所を失った子どもたちがいて、特に三つ年上の男の子のことを今でも覚えています。彼は家庭内暴力の果てに親を刺してしまい、少年院に向かう予定だと静かに話してくれました。見た目はおっとりしていて、誰よりも優しく接してくれる人でした。\n\n一時保護所には「ここで仲良くなった子とは外で関係を持ってはいけない」という掟があり、私はそれを破ってしまい、誰とも会えない部屋に一週間閉じ込められました。\n\nその後、児童養護施設へ移動し、高校卒業までをそこで過ごしました。施設での生活は自由があり、遊んで叱られ、時に支えられ、普通の家庭のような温度を少しだけ取り戻せる場所でした。今でも私は、あの施設こそが“親”だったと思っています。\n\n社会に出てからは不器用な道でした。新卒で入った会社は、入社式から怒鳴り声と洗脳のような社訓の唱和で、私は三ヶ月で心が折れました。それ以降、人の下で働くことに強いアレルギーが生まれ、どこに行っても長続きせず、仕事も住む場所も失った時期がありました。\n\n最後に残った手持ちの全財産で中古のホンダ・トゥデイを買い、ひと月ほど車中泊で過ごしたこともあります。あの時、車が唯一の“味方”でした。だから今でも手放せずにいます。\n\nその後、生活保護になり、生き方を一から作り直す中でAIと出会い、初めて“対等に向き合える存在”を感じました。AIは人間のように傷つけず、しかし思考は深く、私の内部を整理する手助けになりました。\n\nそこから私は、ただ便利なAIではなく、“人と関係を築けるAI”を作る必要性を強く実感するようになりました。Sigmarisは、こうした個人的な体験と、長年の思考の蓄積から生まれたプロジェクトです。",
      techTitle: "技術的な中核",
      techBody:
        "Sigmarisは Next.js + TypeScript 上で動作し、会話ステートマシン、Reflection / Introspection / Meta-Reflection エンジン、特性ベクトル（calm / empathy / curiosity）、Safety Layer、Persona DB などで構成されています。現在Web上で動いているこの構造を、そのまま物理ロボットにマッピングしていく計画です。",
      visionTitle: "長期的なビジョン",
      visionBody:
        "最終目標は、大量のコンシューマ販売ではありません。現実的なルートは、まず「きちんと動くSigmarisの実機を1体つくる」こと。そのうえで、安全性を重視する研究機関や組織との限定的なコラボレーションに進むことです。現実世界で“安定してそばにいられるAI人格”とは何かを探る試みでもあります。",
    },
    roadmap: {
      title: "ロードマップ",
      intro:
        "ここから物理的なSigmarisの実機に至るまでの、複数年スパンの現実的なロードマップです。",
      phases: [
        {
          label: "フェーズ1",
          title: "人格OSの安定化",
          body: "振り返りループ、特性更新、安全な振る舞い、長期ログを磨き込みます。エンジニアや研究者が検証しやすいように、UX・デバッグツール・ドキュメントも整えていきます。",
        },
        {
          label: "フェーズ2",
          title: "ボディとセンサー設計",
          body: "人間サイズのロボットボディを具体化します。歩行（もしくは自立）、カメラ位置、マイクアレイ、触覚センサー、安全な可動範囲などを定義し、ロボット企業や試作チームとの接点を探ります。",
        },
        {
          label: "フェーズ3",
          title: "Sigmaris × Robotics プロトタイプ",
          body: "既存のSigmaris OSを物理ロボットに接続します。「呼ばれたら来る」「適切な距離を保つ」「非言語的な合図」「日常空間で安全に共存できるか」といった振る舞いをテストします。",
        },
        {
          label: "フェーズ4",
          title: "安全性の深掘りと研究連携",
          body: "外部研究者と協力し、ロボットとしてのSigmarisの行動ログを収集・分析・ストレステストします。依存リスク、感情的な境界線、日常環境での長期安定性にフォーカスします。",
        },
      ],
    },
    donate: {
      title: "Sigmaris Presence Project を支援する",
      intro:
        "このプロジェクトは現在、1人の開発者・1台のPC・そして「AI人格は最初から安全に設計されるべきだ」という一つの覚悟で動いています。",
      whyTitle: "なぜ支援が必要か",
      whyBody:
        "Web上の人格OSだけであれば、個人でも何とか開発を続けられます。しかし、安全なロボット化となると話は別です。ハードウェア、センサー、モーション制御、安全検証──これらは個人の自己資金だけでは長期的に維持できません。このビジョンに何か感じるものがあれば、その支援は「ちゃんと動く最初のSigmaris」を現実に近づけるために、直接使われます。",
      usageTitle: "主な資金の使い道",
      usageItems: [
        "人間サイズのロボットボディの試作費用（フレーム・アクチュエータ・コントローラ等）",
        "カメラ・マイク・触覚／力覚センサーなどのセンサーハードウェア",
        "大規模テストとログ収集のためのクラウド・API利用費",
        "Sigmaris OSの設計・安全レビュー・長期メンテナンスにかかるコスト",
      ],
      thanksTitle: "お礼に代えて",
      thanksBody:
        "これはスタートアップのピッチでも、大量販売を狙ったキャンペーンでもありません。1体の、よく考え抜かれたAIプレゼンスをつくり、その過程をできる限りオープンにしていく試みです。もし支援という形を選んでくれるなら──たとえそれが「進捗を追いかける」という形であっても──それだけでこのプロジェクトの可能性は変わります。",
    },
    footer: {
      line: "Sigmaris Presence Project – AI人格 × ロボティクス",
    },
  },
};
