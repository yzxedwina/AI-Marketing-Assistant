import React, { useCallback, useEffect, useRef, useState } from "react";
// The profile center keeps user-entered facts separate from platform API data.
import {
  ArrowLeft,
  ArrowRight,
  BarChart3,
  Check,
  Clipboard,
  Database,
  FileText,
  History as HistoryIcon,
  LayoutDashboard,
  Link2,
  MessageCircle,
  PenLine,
  RefreshCw,
  ShieldCheck,
  Target,
  UserRound,
  X,
} from "lucide-react";

const NAV = [
  ["console", "中控台", LayoutDashboard],
  ["profile", "用户画像", UserRound],
  ["market", "市场洞察", BarChart3],
  ["decision", "商业机会", Target],
  ["plan", "营销方案", PenLine],
  ["history", "历史与复盘", HistoryIcon],
];
const AUTH_KEY = "ama-auth-session";
const API_BASE =
  import.meta.env.VITE_API_BASE_URL ||
  (import.meta.env.DEV ? "http://127.0.0.1:8000" : window.location.origin);
function readSession() {
  try {
    return JSON.parse(localStorage.getItem(AUTH_KEY));
  } catch {
    return null;
  }
}
function currentUserId() {
  return readSession()?.user?.user_id || "";
}
function accountStorageKey(key) {
  return currentUserId() ? key + ":" + currentUserId() : key;
}
function authHeaders() {
  const token = readSession()?.access_token;
  return {
    "Content-Type": "application/json",
    ...(token ? { Authorization: "Bearer " + token } : {}),
  };
}
async function postAI(path, payload) {
  const response = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify(payload),
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.detail || "AI 服务暂时不可用");
  return data;
}
async function postAPI(path, payload = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify(payload),
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.detail || "操作暂时无法完成");
  return data;
}
async function putAPI(path, payload) {
  const response = await fetch(`${API_BASE}${path}`, {
    method: "PUT",
    headers: authHeaders(),
    body: JSON.stringify(payload),
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.detail || "数据保存失败");
  return data;
}
async function getAPI(path) {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: authHeaders(),
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.detail || "评分服务暂时不可用");
  return data;
}
function profilePayload(profile) {
  const { goal, direction, customers, topics, styles, services, boundaries, status } =
    profile;
  return {
    goal,
    direction,
    customers,
    topics,
    styles,
    services,
    boundaries,
    status,
    capacity: profile.capacity || "",
    manual_platform_data: profile.manualPlatformData || {},
    existing_businesses: profile.existingBusinesses || [],
  };
}
function createBusinessDraft() {
  return {
    id: `business-${Date.now()}-${Math.random().toString(16).slice(2)}`,
    name: "",
    businessType: "",
    durationRange: "",
    showcaseType: "",
    showcaseTypeOther: "",
    description: "",
    finishedContent: "",
    preferredType: "",
    excludedType: "",
    priceMin: "",
    priceMax: "",
    weeklyCapacity: "",
  };
}
const EMPTY_PROFILE = {
  goal: "",
  direction: "",
  customers: "",
  topics: "",
  styles: "",
  services: "",
  boundaries: "",
  capacity: "",
  status: "可接单",
  existingBusinesses: [],
  manualPlatformData: {
    xiaohongshu: {
      accountName: "",
      followers: "",
      recentPosts: "",
      averageViews: "",
      averageFavorites: "",
      averageComments: "",
    },
    huajia: {
      accountName: "",
      showcaseCount: "",
      favorites: "",
      completedOrders: "",
    },
  },
};
const DEFAULT_PROFILE = {
  goal: "提高自然流量",
  direction: "动物主题手绘插画",
  customers: "宠物用户、兽设 OC 客户",
  topics: "宠物、兽设",
  styles: "水彩、平涂",
  services: "带场景插图、动物大头挂件",
  boundaries: "不承接电子插画；拒绝写实人像",
  capacity: "12 小时 / 周",
  status: "可接单",
  existingBusinesses: [],
  manualPlatformData: EMPTY_PROFILE.manualPlatformData,
};
const OPS = [
  {
    score: 76,
    name: "动物大头手绘挂件",
    level: "建议优先验证",
    support: [
      "水彩与平涂能力匹配",
      "3 天交付周期适合轻量测试",
      "价格带与现有业务一致",
    ],
    risk: ["真实成交字段仍不足", "小红书近期发布样本较少"],
    missing: ["画加近 30 天成交量"],
    confidence: "中等",
  },
  {
    score: 68,
    name: "宠物纪念插画",
    level: "可作为备选",
    support: ["宠物题材经验明确", "用户愿意继续承接"],
    risk: ["单件制作周期较长"],
    missing: ["同价位咨询转化"],
    confidence: "中等",
  },
  {
    score: 61,
    name: "兽设场景插图",
    level: "建议继续观察",
    support: ["已有同类约稿作品"],
    risk: ["每周仅能完成约一张", "市场供给变化不明确"],
    missing: ["细分类目新增橱窗数"],
    confidence: "偏低",
  },
];

function useStored(key, initial) {
  const storageKey =
    key === "ama-route" || !currentUserId() ? key : key + ":" + currentUserId();
  const [v, setV] = useState(() => {
    try {
      return JSON.parse(localStorage.getItem(storageKey)) ?? initial;
    } catch {
      return initial;
    }
  });
  useEffect(
    () => localStorage.setItem(storageKey, JSON.stringify(v)),
    [storageKey, v],
  );
  return [v, setV];
}
const Button = ({
  children,
  onClick,
  light = false,
  type = "button",
  disabled = false,
}) => (
  <button
    type={type}
    className={"btn " + (light ? "light" : "")}
    onClick={onClick}
    disabled={disabled}
  >
    {children}
  </button>
);
const Card = ({ children, c = "" }) => (
  <section className={"card " + c}>{children}</section>
);
const Chip = ({ children, green = false }) => (
  <span className={"chip " + (green ? "green" : "")}>{children}</span>
);
function Head({ title, sub, action, back }) {
  return (
    <div className="head">
      <div>
        {back && (
          <button className="textBack" onClick={back}>
            <ArrowLeft size={16} />
            返回
          </button>
        )}
        <h1>{title}</h1>
        <p>{sub}</p>
      </div>
      {action}
    </div>
  );
}
const Note = ({ children }) => (
  <div className="inlineNote">
    <ShieldCheck size={17} />
    {children}
  </div>
);

function Landing({ go }) {
  return (
    <>
      <header className="top">
        <b>AI 营销助手</b>
        <nav>
          <a href="#services">服务方式</a>
          <a href="#boundary">产品边界</a>
          <Button light onClick={() => go("login")}>
            登录
          </Button>
          <Button onClick={() => go("login")}>开始使用</Button>
        </nav>
      </header>
      <main className="hero">
        <div>
          <small>为独立插画师设计</small>
          <h1>把市场信号，变成你真正能执行的经营方向</h1>
          <p>
            结合你的创作能力与产能，从画加和小红书的公开数据中整理机会、证据和可编辑的营销方案。
          </p>
          <Button onClick={() => go("login")}>
            登录并开始 <ArrowRight size={17} />
          </Button>
        </div>
        <Card c="preview">
          <div className="row">
            <b>本周经营建议</b>
            <Chip green>信息可用</Chip>
          </div>
          <h2>轻量恢复小红书自然流量</h2>
          <div className="score">
            <strong>76</strong>
            <span>
              动物大头手绘挂件
              <br />
              画像匹配 · 产能适配
            </span>
          </div>
          <div className="bars">
            <i />
            <i />
            <i />
          </div>
        </Card>
      </main>
      <section id="services" className="features">
        {[
          ["卖什么", "识别与你能力、价格和产能匹配的业务方向。"],
          ["怎么卖", "整理定位、客户、卖点和低压力发布节奏。"],
          ["发什么", "生成可修改的图文方案或视频文字脚本。"],
        ].map((x) => (
          <Card key={x[0]}>
            <h3>{x[0]}</h3>
            <p>{x[1]}</p>
          </Card>
        ))}
      </section>
      <section id="boundary" className="boundary">
        <h2>决定权和账号始终属于你</h2>
        <p>
          我们整理信息与文字方案，不自动发布、不自动私信，也不承诺曝光、咨询或成交。
        </p>
      </section>
    </>
  );
}

function Login({ go, onLogin }) {
  const [mode, setMode] = useState("password"),
    [number, setNumber] = useState(""),
    [code, setCode] = useState(""),
    [account, setAccount] = useState(""),
    [password, setPassword] = useState(""),
    [pending, setPending] = useState(false),
    [error, setError] = useState("");
  const submitPassword = async (event) => {
    event.preventDefault();
    setPending(true);
    setError("");
    try {
      const session = await postAPI("/auth/login", {
        username: account,
        password,
      });
      localStorage.setItem(AUTH_KEY, JSON.stringify(session));
      await onLogin(session);
    } catch (loginError) {
      setError(loginError.message);
    } finally {
      setPending(false);
    }
  };
  return (
    <div className="split">
      <section className="story">
        <b>AI 营销助手</b>
        <div>
          <h1>先理解你的经营状态，再给出可以验证的方向。</h1>
          <p>
            你的能力、产能和边界始终由你确认；AI
            只在真实信息与证据范围内提供建议。
          </p>
          {[
            "结合画加专业市场事实",
            "参考小红书趋势信号",
            "同时展示支持与反向证据",
          ].map((x) => (
            <p className="tick" key={x}>
              <Check size={15} />
              {x}
            </p>
          ))}
        </div>
      </section>
      <section className="login">
        <Card c="loginCard">
          <div className="loginSwitches" aria-label="切换登录方式">
            {mode !== "phone" && (
              <button className="link" onClick={() => setMode("phone")}>
                手机验证码登录
              </button>
            )}
            {mode !== "password" && (
              <button className="link" onClick={() => setMode("password")}>
                账号密码登录
              </button>
            )}
            {mode !== "social" && (
              <button className="link" onClick={() => setMode("social")}>
                第三方登录
              </button>
            )}
          </div>
          <h2>登录 AI 营销助手</h2>
          <p>登录后继续完成经营平台连接与首次设置。</p>
          {mode === "phone" ? (
            <form
              onSubmit={(e) => {
                e.preventDefault();
                setError("手机验证码登录将在正式接入短信服务后开放，请先使用分发账号。");
              }}
            >
              <label>
                手机号
                <input
                  name="phone"
                  autoComplete="tel"
                  inputMode="tel"
                  value={number}
                  onChange={(e) => setNumber(e.target.value)}
                  placeholder="输入手机号"
                />
              </label>
              <label>
                验证码
                <div className="codeRow">
                  <input
                    name="code"
                    autoComplete="one-time-code"
                    inputMode="numeric"
                    value={code}
                    onChange={(e) => setCode(e.target.value)}
                    placeholder="输入验证码"
                  />
                  <Button light>获取验证码</Button>
                </div>
              </label>
              <Button type="submit" disabled={!number || !code}>
                验证并继续
              </Button>
            </form>
          ) : mode === "password" ? (
            <form onSubmit={submitPassword}>
              <label>
                账号
                <input
                  name="account"
                  autoComplete="username"
                  value={account}
                  onChange={(e) => setAccount(e.target.value)}
                  placeholder="输入手机号或账号"
                />
              </label>
              <label>
                密码
                <input
                  name="password"
                  type="password"
                  autoComplete="current-password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="输入密码"
                />
              </label>
              {error && <p className="formError">{error}</p>}
              <Button type="submit" disabled={!account || !password || pending}>
                {pending ? "正在登录…" : "登录并继续"}
              </Button>
            </form>
          ) : (
            <>
              <button className="social" onClick={() => setError("微信登录尚未接入，请使用分发账号。")}>
                <i className="wx" />
                使用微信登录
              </button>
              <button className="social" onClick={() => setError("小红书登录尚未接入，请使用分发账号。")}>
                <i className="xhs" />
                使用小红书登录
              </button>
              <button className="social" onClick={() => setError("画加登录尚未接入，请使用分发账号。")}>
                <i className="huajia" />
                使用画加登录
              </button>
              {error && <p className="formError">{error}</p>}
            </>
          )}
          <small>登录方式只用于身份验证</small>
          <div className="note">
            <b>信息控制权属于你</b>
            <br />
            你可以查看、修改、删除已授权信息，并随时撤回授权。
          </div>
        </Card>
      </section>
    </div>
  );
}

function Setup({ go }) {
  const qs = [
    ["连接你的经营平台", ["小红书", "画加"], true],
    [
      "你这一阶段最想解决什么？",
      [
        "提高自然流量",
        "吸引潜在客户",
        "提高咨询与成交",
        "测试新的业务方向",
        "其他目标",
      ],
      false,
    ],
    [
      "你主要创作哪些题材？",
      ["宠物插画", "兽设与 OC", "头像业务", "场景插画", "其他题材"],
      true,
    ],
    [
      "哪些画风最能代表你？",
      ["水彩", "平涂", "厚涂", "线稿与黑白", "其他画风"],
      true,
    ],
  ];
  const [s, setS] = useState(0),
    [answers, setAnswers] = useStored("ama-onboarding", [[], [], [], []]);
  const cur = answers[s] || [];
  const choose = (x) =>
    setAnswers((a) =>
      a.map((v, i) =>
        i !== s
          ? v
          : qs[s][2]
            ? v.includes(x)
              ? v.filter((y) => y !== x)
              : [...v, x]
            : [x],
      ),
    );
  const next = () => (s === 3 ? go("product") : setS(s + 1));
  return (
    <div className="setup">
      <header>
        <b>AI 营销助手</b>
        <span>首次设置</span>
      </header>
      <div className="steps" aria-label={`第 ${s + 1} 步，共 4 步`}>
        {qs.map((_, i) => (
          <i className={i < s ? "done" : i === s ? "now" : ""} key={i}>
            {i < s ? <Check size={11} /> : null}
          </i>
        ))}
      </div>
      <main>
        <p className="stepLabel">{s + 1} / 4</p>
        <h1>{qs[s][0]}</h1>
        <p>选择最符合你的选项，稍后仍可以在用户画像中修改。</p>
        <div className="options">
          {qs[s][1].map((x) => (
            <button
              className={cur.includes(x) ? "selected" : ""}
              onClick={() => choose(x)}
              key={x}
            >
              <span>
                <b>{x}</b>
                <small>用于生成本轮画像与建议</small>
              </span>
              <i>{cur.includes(x) ? <Check size={15} /> : null}</i>
            </button>
          ))}
        </div>
        {cur.some((x) => x.startsWith("其他")) && (
          <label>
            补充说明
            <input placeholder="写下你的选项" />
          </label>
        )}
        <div className="right">
          {s > 0 && (
            <Button light onClick={() => setS(s - 1)}>
              返回
            </Button>
          )}
          <Button light onClick={next}>
            跳过
          </Button>
          <Button onClick={next}>{s === 3 ? "完成设置" : "下一步"}</Button>
        </div>
        <div className="control">
          <b>信息控制权属于你</b>
          <span>价格、产能和禁区请在用户画像中维护。</span>
        </div>
      </main>
    </div>
  );
}

function Sidebar({ view, setView, goLanding, chatThreads, activeChatId, openThread, newThread, displayName, onLogout }) {
  return (
    <aside className="side">
      <button className="brandHome" onClick={goLanding} aria-label="返回 AI 营销助手落地页">
        AI 营销助手
      </button>
      <nav aria-label="产品主导航">
        {NAV.map(([id, n, I]) => (
          <button
            className={view === id ? "active" : ""}
            onClick={() => setView(id)}
            key={id}
          >
            <I size={18} />
            {n}
          </button>
        ))}
      </nav>
      <section className="sideChats" aria-label="历史对话">
        <div className="sideChatsHead">
          <span>历史对话</span>
          <button onClick={newThread} aria-label="开始新对话">
            <PenLine size={15} />
          </button>
        </div>
        <div className="sideChatList">
          {chatThreads.length ? (
            chatThreads.slice(0, 5).map((thread) => (
              <button
                className={view === "chat" && activeChatId === thread.id ? "active" : ""}
                onClick={() => openThread(thread.id)}
                key={thread.id}
                title={thread.title}
              >
                <MessageCircle size={16} />
                <span>{thread.title}</span>
              </button>
            ))
          ) : (
            <p>完成一次提问后，对话会保存在这里。</p>
          )}
        </div>
      </section>
      <div className="person">
        <i />
        <span>
          <b>{displayName || "体验用户"}</b>
          <small>独立插画师</small>
        </span>
        <button className="logoutLink" type="button" onClick={onLogout}>退出</button>
      </div>
    </aside>
  );
}
function Console({ go, profile, profileEstablished, openChat }) {
  const [question, setQuestion] = useState("");
  const displayName = readSession()?.user?.display_name || "创作者";
  const focusTitle = profileEstablished
    ? profile.goal || "确认本轮经营目标"
    : "先建立用户画像，再开始机会分析";
  const focusDescription = profileEstablished
    ? `当前方向：${profile.direction || "待补充"}。系统会结合画像与最新市场信息生成候选机会。`
    : "填写经营目标、创作能力和现有业务后，系统才能生成与你匹配的建议。";
  return (
    <div className="consolePage">
      <Head
        title="创作者中控台"
        sub={`你好，${displayName}。这里是你需要关注的经营动态。`}
        action={<Button onClick={() => go(profileEstablished ? "decision" : "profile")}>{profileEstablished ? "开始新分析" : "建立画像"}</Button>}
      />
      <section className="focusCard">
        <div>
          <small>{profileEstablished ? "本轮营销目标" : "开始使用"}</small>
          <h2>{focusTitle}</h2>
          <p>{focusDescription}</p>
        </div>
        <Button light onClick={() => go(profileEstablished ? "decision" : "profile")}>
          {profileEstablished ? "查看本轮目标" : "填写画像"} <ArrowRight size={15} />
        </Button>
      </section>
      <div className="sectionTitle">
        <h3>你的当前状态</h3>
        <span>今天 09:30 更新</span>
      </div>
      <div className="statusGrid">
        <Card c="statusSuccess">
          <small>画像状态</small>
          <h3>{profileEstablished ? "已确认" : "未建立"}</h3>
          <p>{profileEstablished ? "稳定信息已按当前账号保存" : "需要填写经营与创作信息"}</p>
        </Card>
        <Card>
          <small>本周产能</small>
          <h3>{profileEstablished ? profile.status : "待填写"}</h3>
          <p>{profileEstablished ? profile.capacity || "可在画像中更新" : "建立画像后显示"}</p>
        </Card>
        <Card>
          <small>营销需求</small>
          <h3 className="brandText">{profileEstablished ? profile.goal : "待确认"}</h3>
          <p>{profileEstablished ? "可在商业机会中开始本轮分析" : "建立画像后显示"}</p>
        </Card>
      </div>
      <div className="sectionTitle">
        <h3>最新动态</h3>
        <span>按需要你处理的顺序排列</span>
      </div>
      <div className="flowPrimary">
        <Card c="opportunityCard">
          <div className="row">
            <small className="brandText">{profileEstablished ? "新的商业机会" : "商业机会"}</small>
            <Chip>{profileEstablished ? "待分析" : "需先建档"}</Chip>
          </div>
          <h2>{profileEstablished ? "基于当前画像生成候选方向" : "完成画像后生成商业机会"}</h2>
          <p>{profileEstablished ? "系统将结合你的能力、业务边界、产能与最新市场证据进行规则评分。" : "这里不会使用其他账号的资料，也不会用示例内容冒充你的分析结果。"}</p>
          <div className="microTags">
            <span>{profileEstablished ? "画像可用" : "画像缺失"}</span>
            <span>规则评分</span>
            <span>证据可追溯</span>
          </div>
          <button className="inlineAction" onClick={() => go("decision")}>
            查看完整证据 <ArrowRight size={14} />
          </button>
        </Card>
        <Card c="dataCard">
          <small>数据动态</small>
          <h3>公共市场数据可更新</h3>
          <div className="metricRow">
            <span>小红书垂直领域样本</span>
            <b>最多 20 条</b>
          </div>
          <div className="metricRow">
            <span>画加公开橱窗样本</span>
            <b>最多 20 条</b>
          </div>
          <p className="fineprint">实际数量取决于公开页面可用性与平台安全限制。</p>
          <button className="inlineAction" onClick={() => go("market")}>
            查看市场洞察 <ArrowRight size={14} />
          </button>
        </Card>
      </div>
      <div className="flowSecondary">
        <Card>
          <div className="row">
            <small>方案进度</small>
            <span className="warningText">{profileEstablished ? "尚未生成" : "需先建档"}</span>
          </div>
          <h3>{profileEstablished ? "生成本轮内容方案" : "建立画像后生成方案"}</h3>
          <button className="inlineAction" onClick={() => go("plan")}>
            继续编辑 <ArrowRight size={14} />
          </button>
        </Card>
        <Card>
          <div className="row">
            <small>结果反馈</small>
            <span className="warningText">暂无记录</span>
          </div>
          <h3>发布后的真实结果将在这里复盘</h3>
          <button className="inlineAction" onClick={() => go("history")}>
            回填表现 <ArrowRight size={14} />
          </button>
        </Card>
      </div>
      <form
        className="assistantComposer"
        onSubmit={(e) => {
          e.preventDefault();
          if (question.trim()) {
            openChat(question);
            setQuestion("");
          }
        }}
      >
        <MessageCircle size={18} aria-hidden="true" />
        <input
          aria-label="询问营销助理"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="问营销助理：我今天应该先处理什么？"
        />
        <button type="submit" aria-label="发送问题" disabled={!question.trim()}>
          <ArrowRight size={18} />
        </button>
      </form>
    </div>
  );
}

function Chat({ messages, setMessages, go, profile }) {
  const [draft, setDraft] = useState(""),
    [pending, setPending] = useState(false),
    endRef = useRef(null),
    inFlightRef = useRef(false);
  useEffect(() => {
    endRef.current?.scrollIntoView({ block: "end" });
  }, [messages]);
  useEffect(() => {
    const last = messages[messages.length - 1];
    if (!last || last.role !== "user" || inFlightRef.current) return;
    const run = async () => {
      inFlightRef.current = true;
      setPending(true);
      try {
        const response = await fetch(`${API_BASE}/ai/chat`, {
          method: "POST",
          headers: authHeaders(),
          body: JSON.stringify({
            user_id: currentUserId(),
            profile,
            messages: messages
              .slice(-8)
              .map((item) => ({ role: item.role, content: item.text })),
          }),
        });
        const data = await response.json().catch(() => ({}));
        if (!response.ok) throw new Error(data.detail || "AI 服务暂时不可用");
        setMessages((current) => [
          ...current,
          {
            role: "assistant",
            text: data.reply,
            meta: {
              model: data.model,
              citations: data.citations || [],
              ragStatus: data.rag_status,
              memoryLoaded: data.memory_loaded,
            },
          },
        ]);
      } catch (error) {
        setMessages((current) => [
          ...current,
          {
            role: "assistant",
            text: `暂时无法连接 AI 服务：${error.message}。你可以稍后重试，本次问题不会被当作画像事实。`,
            error: true,
          },
        ]);
      } finally {
        inFlightRef.current = false;
        setPending(false);
      }
    };
    run();
  }, [messages, profile, setMessages]);
  const send = (e) => {
    e.preventDefault();
    const text = draft.trim();
    if (!text || pending) return;
    setMessages((current) => [...current, { role: "user", text }]);
    setDraft("");
  };
  return (
    <div className="chatPage">
      <header className="chatHeader">
        <button className="textBack" onClick={() => go("console")}>
          <ArrowLeft size={16} />
          返回中控台
        </button>
        <div>
          <h1>营销助理</h1>
          <p>基于已确认画像与证据回答，不补写缺失数字。</p>
        </div>
      </header>
      <section className="chatMessages" aria-live="polite">
        {messages.length === 0 ? (
          <div className="chatEmpty">
            <MessageCircle size={24} />
            <h2>从经营问题开始</h2>
            <p>例如：我今天应该先确认机会方向，还是先补充画像？</p>
          </div>
        ) : (
          messages.map((item, index) => (
            <div
              className={
                "chatMessage " + item.role + (item.error ? " error" : "")
              }
              key={index}
            >
              <span>{item.role === "user" ? "你" : "营销助理"}</span>
              <p>{item.text}</p>
              {item.meta && (
                <small>
                  {item.meta.citations.length
                    ? `参考知识：${item.meta.citations.join("、")}`
                    : "本轮未引用知识库条目"}
                </small>
              )}
            </div>
          ))
        )}
        {pending && (
          <div className="chatMessage assistant pending">
            <span>营销助理</span>
            <p>正在结合你的画像与相关证据整理回答…</p>
          </div>
        )}
        <div ref={endRef} />
      </section>
      <form className="chatComposer" onSubmit={send}>
        <MessageCircle size={18} aria-hidden="true" />
        <input
          aria-label="向营销助理发送消息"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          placeholder="继续询问营销助理…"
          disabled={pending}
        />
        <button
          type="submit"
          aria-label="发送消息"
          disabled={!draft.trim() || pending}
        >
          <ArrowRight size={18} />
        </button>
      </form>
    </div>
  );
}

function Profile({
  profile,
  setProfile,
  profileEstablished,
  setProfileEstablished,
  toast,
}) {
  const [page, setPage] = useState("overview"),
    [draft, setDraft] = useState(profile),
    [candidates, setCandidates] = useState([
      ["题材候选", "宠物纪念与兽设"],
      ["视觉特点", "水彩晕染、清晰轮廓"],
      ["可发展业务", "宠物纪念挂件"],
    ]),
    [aiPending, setAiPending] = useState(false);
  const beginProfile = () => {
    setDraft(profileEstablished ? profile : structuredClone(EMPTY_PROFILE));
    setPage("edit");
  };
  const updateManualField = (platform, field, value) => {
    setDraft((current) => ({
      ...current,
      manualPlatformData: {
        ...(current.manualPlatformData || EMPTY_PROFILE.manualPlatformData),
        [platform]: {
          ...(current.manualPlatformData?.[platform] ||
            EMPTY_PROFILE.manualPlatformData[platform]),
          [field]: value,
        },
      },
    }));
  };
  const updateBusinessField = (id, field, value) => {
    setDraft((current) => ({
      ...current,
      existingBusinesses: (current.existingBusinesses || []).map((business) =>
        business.id === id ? { ...business, [field]: value } : business,
      ),
    }));
  };
  const removeBusiness = (id) => {
    setDraft((current) => ({
      ...current,
      existingBusinesses: (current.existingBusinesses || []).filter(
        (business) => business.id !== id,
      ),
    }));
  };
  const analyzeCandidates = async () => {
    setAiPending(true);
    try {
      const data = await postAI("/ai/profile-candidates", {
        user_id: currentUserId(),
        source_text: `当前画像摘要：${profile.topics}；${profile.styles}；${profile.services}；${profile.boundaries}`,
      });
      setCandidates(
        data.candidates.map((item) => [
          item.field,
          Array.isArray(item.value)
            ? item.value.join("、")
            : String(item.value),
          item.confidence,
          item.basis,
        ]),
      );
      toast("AI 候选画像已更新");
    } catch (error) {
      toast(error.message);
    } finally {
      setAiPending(false);
    }
  };
  const save = async () => {
    const required = [
      ["goal", "当前经营目标"],
      ["direction", "业务方向"],
      ["customers", "目标客户"],
      ["topics", "擅长题材"],
      ["styles", "代表画风"],
      ["services", "可承接业务"],
      ["boundaries", "不接类型"],
    ];
    const missing = required.find(([key]) => !draft[key]?.trim());
    if (missing) {
      toast(`请先填写${missing[1]}`);
      return;
    }
    const businessRequiredFields = [
      ["name", "业务名称"],
      ["businessType", "业务类型"],
      ["showcaseType", "橱窗类型"],
      ["finishedContent", "成稿内容"],
      ["excludedType", "不接类型"],
    ];
    for (const [index, business] of (draft.existingBusinesses || []).entries()) {
      const missingBusinessField = businessRequiredFields.find(
        ([key]) => !String(business[key] || "").trim(),
      );
      if (missingBusinessField) {
        toast(`请填写第 ${index + 1} 项现有业务的${missingBusinessField[1]}`);
        return;
      }
      if (business.showcaseType === "其他" && !business.showcaseTypeOther?.trim()) {
        toast(`请填写第 ${index + 1} 项现有业务的其他橱窗类型`);
        return;
      }
    }
    try {
      const data = await putAPI(
        "/workflow/profile/" + currentUserId(),
        profilePayload(draft),
      );
      const {
        manual_platform_data: savedManualData,
        existing_businesses: savedBusinesses,
        ...savedProfileFields
      } = data.ui_profile || {};
      setProfile({
        ...draft,
        ...savedProfileFields,
        manualPlatformData: savedManualData || draft.manualPlatformData,
        existingBusinesses: savedBusinesses || draft.existingBusinesses,
      });
      setProfileEstablished(true);
      toast("用户画像已更新并写入长期记忆");
      setPage("overview");
    } catch (error) {
      toast(error.message);
    }
  };
  if (page === "edit")
    return (
      <>
        <Head
          title="编辑用户画像"
          sub="修改后将影响下一轮机会分析。"
          back={() => setPage("overview")}
        />
        <Card c="profileFormCard">
          <div className="profileFormIntro">
            <div>
              <h2>经营与创作信息</h2>
              <p>标记为必填的信息将用于机会匹配；产能信息可以稍后补充。</p>
            </div>
            <Chip>用户填写</Chip>
          </div>
          <div className="form two">
            {[
              ["goal", "当前经营目标 *"],
              ["direction", "业务方向 *"],
              ["customers", "目标客户 *"],
              ["topics", "擅长题材 *"],
              ["styles", "代表画风 *"],
              ["services", "可承接业务 *"],
              ["capacity", "每周产能"],
              ["boundaries", "不接类型 *"],
            ].map(([k, l]) => (
              <label key={k}>
                {l}
                <input
                  value={draft[k]}
                  onChange={(e) => setDraft({ ...draft, [k]: e.target.value })}
                />
              </label>
            ))}
          </div>
          <label>
            当前产能状态
            <select
              value={draft.status}
              onChange={(e) => setDraft({ ...draft, status: e.target.value })}
            >
              <option>可接单</option>
              <option>交付中</option>
              <option>满载</option>
              <option>暂停</option>
            </select>
          </label>
          <div className="profileFormDivider" />
          <div className="profileFormIntro existingBusinessIntro">
            <div>
              <h2>现有业务</h2>
              <p>
                这部分不是必填。填写越详细，系统越能准确判断你的业务能力、偏好与承接边界。
              </p>
            </div>
            <label className="businessToggle">
              <input
                type="checkbox"
                checked={Boolean(draft.existingBusinesses?.length)}
                onChange={(event) =>
                  setDraft((current) => ({
                    ...current,
                    existingBusinesses: event.target.checked
                      ? current.existingBusinesses?.length
                        ? current.existingBusinesses
                        : [createBusinessDraft()]
                      : [],
                  }))
                }
              />
              <span>我有现有业务</span>
            </label>
          </div>
          {Boolean(draft.existingBusinesses?.length) && (
            <div className="existingBusinessEditor">
              {draft.existingBusinesses.map((business, index) => (
                <section className="businessEditorCard" key={business.id}>
                  <div className="businessEditorHeading">
                    <div>
                      <Chip>业务 {index + 1}</Chip>
                      <h3>{business.name || "未命名业务"}</h3>
                    </div>
                    <button
                      type="button"
                      className="removeBusinessButton"
                      onClick={() => removeBusiness(business.id)}
                    >
                      移除
                    </button>
                  </div>
                  <div className="form two businessCoreFields">
                    <label>
                      业务名称 *
                      <input
                        value={business.name}
                        onChange={(event) =>
                          updateBusinessField(business.id, "name", event.target.value)
                        }
                        placeholder="例如：宠物纪念头像"
                      />
                    </label>
                    <label>
                      业务类型 *
                      <select
                        value={business.businessType}
                        onChange={(event) =>
                          updateBusinessField(
                            business.id,
                            "businessType",
                            event.target.value,
                          )
                        }
                      >
                        <option value="">请选择业务类型</option>
                        {[
                          "邀请业务",
                          "普通橱窗",
                          "快速橱窗",
                          "24小时特快橱窗",
                        ].map((option) => (
                          <option key={option}>{option}</option>
                        ))}
                      </select>
                    </label>
                    <label>
                      工期范围
                      <input
                        value={business.durationRange}
                        onChange={(event) =>
                          updateBusinessField(
                            business.id,
                            "durationRange",
                            event.target.value,
                          )
                        }
                        placeholder="例如：3–7 天"
                      />
                    </label>
                    <label>
                      最低价格（元）
                      <input
                        inputMode="decimal"
                        value={business.priceMin}
                        onChange={(event) =>
                          updateBusinessField(business.id, "priceMin", event.target.value)
                        }
                        placeholder="例如：100"
                      />
                    </label>
                    <label>
                      最高价格（元）
                      <input
                        inputMode="decimal"
                        value={business.priceMax}
                        onChange={(event) =>
                          updateBusinessField(business.id, "priceMax", event.target.value)
                        }
                        placeholder="例如：600"
                      />
                    </label>
                    <label>
                      每周可完成数量
                      <input
                        inputMode="numeric"
                        value={business.weeklyCapacity}
                        onChange={(event) =>
                          updateBusinessField(
                            business.id,
                            "weeklyCapacity",
                            event.target.value,
                          )
                        }
                        placeholder="例如：2"
                      />
                    </label>
                    <label>
                      橱窗类型 *
                      <select
                        value={business.showcaseType}
                        onChange={(event) =>
                          updateBusinessField(
                            business.id,
                            "showcaseType",
                            event.target.value,
                          )
                        }
                      >
                        <option value="">请选择橱窗类型</option>
                        {["头像", "Q版全身", "半身像", "立绘", "组合页", "服设", "其他"].map(
                          (option) => (
                            <option key={option}>{option}</option>
                          ),
                        )}
                      </select>
                    </label>
                    {business.showcaseType === "其他" && (
                      <label className="fullField">
                        其他橱窗类型 *
                        <input
                          value={business.showcaseTypeOther}
                          onChange={(event) =>
                            updateBusinessField(
                              business.id,
                              "showcaseTypeOther",
                              event.target.value,
                            )
                          }
                          placeholder="请填写具体类型"
                        />
                      </label>
                    )}
                    <label className="fullField">
                      业务描述
                      <textarea
                        value={business.description}
                        onChange={(event) =>
                          updateBusinessField(
                            business.id,
                            "description",
                            event.target.value,
                          )
                        }
                        placeholder="服务对象、交付方式、可提供的内容等"
                      />
                    </label>
                    <label>
                      成稿内容 *
                      <textarea
                        value={business.finishedContent}
                        onChange={(event) =>
                          updateBusinessField(
                            business.id,
                            "finishedContent",
                            event.target.value,
                          )
                        }
                        placeholder="最终交付给客户的内容"
                      />
                    </label>
                    <label>
                      偏好类型
                      <textarea
                        value={business.preferredType}
                        onChange={(event) =>
                          updateBusinessField(
                            business.id,
                            "preferredType",
                            event.target.value,
                          )
                        }
                        placeholder="更愿意承接的题材或客户需求"
                      />
                    </label>
                    <label className="fullField">
                      不接类型 *
                      <textarea
                        value={business.excludedType}
                        onChange={(event) =>
                          updateBusinessField(
                            business.id,
                            "excludedType",
                            event.target.value,
                          )
                        }
                        placeholder="明确不承接的题材、用途或交付要求"
                      />
                    </label>
                  </div>
                </section>
              ))}
              <Button
                light
                onClick={() =>
                  setDraft((current) => ({
                    ...current,
                    existingBusinesses: [
                      ...(current.existingBusinesses || []),
                      createBusinessDraft(),
                    ],
                  }))
                }
              >
                增加业务
              </Button>
            </div>
          )}
          <div className="profileFormDivider" />
          <div className="profileFormIntro">
            <div>
              <h2>手动补充平台信息</h2>
              <p>小红书和画加 API 尚未接入。以下均为可选项，填写后会注明来源为用户提供。</p>
            </div>
            <Chip>可选</Chip>
          </div>
          <h3 className="platformFormTitle">小红书</h3>
          <div className="form two">
            {[
              ["accountName", "账号名称"],
              ["followers", "当前粉丝数"],
              ["recentPosts", "近 30 天发布数"],
              ["averageViews", "近 30 天平均浏览"],
              ["averageFavorites", "近 30 天平均收藏"],
              ["averageComments", "近 30 天平均评论"],
            ].map(([key, label]) => (
              <label key={key}>
                {label}
                <input
                  value={draft.manualPlatformData?.xiaohongshu?.[key] || ""}
                  onChange={(event) =>
                    updateManualField("xiaohongshu", key, event.target.value)
                  }
                  inputMode={key === "accountName" ? "text" : "numeric"}
                />
              </label>
            ))}
          </div>
          <h3 className="platformFormTitle">画加</h3>
          <div className="form two">
            {[
              ["accountName", "账号名称"],
              ["showcaseCount", "当前橱窗数"],
              ["favorites", "橱窗收藏量"],
              ["completedOrders", "近 30 天完成订单"],
            ].map(([key, label]) => (
              <label key={key}>
                {label}
                <input
                  value={draft.manualPlatformData?.huajia?.[key] || ""}
                  onChange={(event) =>
                    updateManualField("huajia", key, event.target.value)
                  }
                  inputMode={key === "accountName" ? "text" : "numeric"}
                />
              </label>
            ))}
          </div>
          <Note>平台信息不会被当成接口数据；保存后仍显示为“用户手动填写”。</Note>
          <div className="right">
            <Button light onClick={() => setPage("overview")}>
              取消
            </Button>
            <Button light onClick={() => toast("草稿已保存在当前设备")}>
              保存草稿
            </Button>
            <Button onClick={save}>保存并确认</Button>
          </div>
        </Card>
      </>
    );
  if (page === "platforms")
    return (
      <>
        <Head
          title="关联平台"
          sub="查看授权范围、重新关联或撤回授权。"
          back={() => setPage("overview")}
        />
        {Object.entries({ 小红书: false, 画加: false }).map(([name, linked]) => (
          <Card c="record" key={name}>
            <div>
              <Chip green={linked}>{linked ? "已关联" : "未关联"}</Chip>
              <h3>{name}</h3>
              <p>
                {linked
                  ? "公开主页、标题、正文和公开数据"
                  : "暂不读取该平台信息"}
              </p>
            </div>
            <div className="buttonRow">
              <Button
                light
                onClick={() => toast("授权范围：公开主页及文字数据")}
              >
                查看授权范围
              </Button>
              <Button
                onClick={() =>
                  toast("当前尚未接入该平台 API，暂时只能手动补充公开信息")
                }
              >
                关联平台
              </Button>
            </div>
          </Card>
        ))}
      </>
    );
  if (page === "candidate")
    return (
      <>
        <Head
          title="AI 候选画像确认"
          sub="候选判断经你确认后才会写入画像。"
          back={() => setPage("overview")}
          action={
            <Button light onClick={analyzeCandidates} disabled={aiPending}>
              {aiPending ? "AI 分析中…" : "AI 分析已授权资料"}
            </Button>
          }
        />
        {candidates.map((x) => (
          <Card c="candidate" key={x[0]}>
            <div>
              <small>{x[0]}</small>
              <h3>{x[1]}</h3>
              <p>
                {x[3]
                  ? `依据：${x[3].join("、")} · 置信度：${x[2]}`
                  : "来源：已授权作品文字信息"}
              </p>
            </div>
            <div className="buttonRow">
              <Button
                light
                onClick={() => {
                  setCandidates((items) => items.filter((item) => item !== x));
                  toast("候选已拒绝");
                }}
              >
                拒绝
              </Button>
              <Button
                onClick={() => toast("候选已确认；正式写入前仍需保存画像")}
              >
                确认
              </Button>
            </div>
          </Card>
        ))}
      </>
    );
  if (page === "changes")
    return (
      <>
        <Head
          title="画像变更记录"
          sub="查看每次确认后的字段和版本变化。"
          back={() => setPage("overview")}
        />
        <Card>
          <div className="table">
            <b>时间</b>
            <b>字段</b>
            <b>变更</b>
            <b>版本</b>
            <span>今天 10:24</span>
            <span>当前目标</span>
            <span>补充“提高自然流量”</span>
            <span>V3</span>
            <span>昨日 18:10</span>
            <span>不接类型</span>
            <span>排除电子插画</span>
            <span>V2</span>
          </div>
        </Card>
      </>
    );
  if (!profileEstablished)
    return (
      <>
        <Head
          title="用户画像中心"
          sub="查看并维护经营目标、能力、产能和不接类型。"
          action={<Button onClick={beginProfile}>编辑画像</Button>}
        />
        <section className="profileEmpty" aria-labelledby="profile-empty-title">
          <div>
            <UserRound size={30} aria-hidden="true" />
            <h2 id="profile-empty-title">还没有关于您的信息…</h2>
            <p>
              建立画像后，系统才能结合你的经营目标、创作能力和不接类型进行分析。
              暂未连接平台时，也可以手动填写信息。
            </p>
            <Button onClick={beginProfile}>建立画像</Button>
          </div>
        </section>
      </>
    );
  const coreFields = [
    profile.goal,
    profile.direction,
    profile.customers,
    profile.topics,
    profile.styles,
    profile.services,
    profile.boundaries,
    profile.capacity,
  ];
  const completedFields = coreFields.filter((value) => value?.trim()).length;
  const completeness = Math.round((completedFields / coreFields.length) * 100);
  const missingLabels = [
    [profile.capacity, "每周产能"],
  ]
    .filter(([value]) => !value?.trim())
    .map(([, label]) => label);
  const manual = profile.manualPlatformData || EMPTY_PROFILE.manualPlatformData;
  const xhsMetrics = manual.xiaohongshu || {};
  const huajiaMetrics = manual.huajia || {};
  const hasAccountMetrics = [
    xhsMetrics.followers,
    xhsMetrics.recentPosts,
    xhsMetrics.averageViews,
    xhsMetrics.averageFavorites,
    xhsMetrics.averageComments,
    huajiaMetrics.showcaseCount,
    huajiaMetrics.favorites,
    huajiaMetrics.completedOrders,
  ].some((value) => String(value || "").trim());
  return (
    <>
      <Head
        title="用户画像中心"
        sub="查看并维护经营目标、能力、产能和不接类型。"
        action={
          <Button onClick={beginProfile}>编辑画像</Button>
        }
      />
      <div className="profileReportTop">
        <Card c="profileAnalysisCard">
          <div className="profileCardHeading">
            <div>
              <small>画像概览</small>
              <h2>{xhsMetrics.accountName || profile.direction}</h2>
            </div>
            <Chip green>画像已确认</Chip>
          </div>
          <div className="profileCompleteness">
            <div>
              <span>资料完整度</span>
              <strong>{completeness}%</strong>
            </div>
            <div className="profileProgressCopy">
              <div className="profileProgress" aria-label={`资料完整度 ${completeness}%`}>
                <i style={{ width: `${completeness}%` }} />
              </div>
              <p>按已填写的 8 项核心字段计算，不代表账号表现。</p>
            </div>
          </div>
          <div className="profileAttention">
            <h3>{missingLabels.length ? "需要补充" : "核心信息已完整"}</h3>
            <p>
              {missingLabels.length
                ? `仍可补充：${missingLabels.join("、")}。填写越完整，机会匹配越准确。`
                : "经营目标、能力、产能和不接类型均已填写。"}
            </p>
          </div>
        </Card>
        <Card c="creatorTypeCard">
          <small>你的创作者方向</small>
          <h2>{profile.direction}</h2>
          <p>目标客户：{profile.customers}</p>
          <div className="creatorStrength">
            <b>核心能力</b>
            <span>{profile.topics}；{profile.styles}</span>
          </div>
          <p className="creatorBoundary">不接类型：{profile.boundaries}</p>
        </Card>
      </div>
      <Card c="profileInsightsCard">
        <div className="sectionHeadingRow">
          <div>
            <h2>画像洞察</h2>
            <p>只展示已确认信息与当前仍缺失的数据。</p>
          </div>
          <Button light onClick={() => setPage("changes")}>查看变更记录</Button>
        </div>
        <div className="profileInsightGrid">
          <div className="profileInsightItem positive">
            <i />
            <div>
              <h3>经营定位清晰</h3>
              <p>{profile.goal}；重点发展{profile.direction}。</p>
            </div>
          </div>
          <div className={`profileInsightItem ${hasAccountMetrics ? "positive" : "pending"}`}>
            <i />
            <div>
              <h3>{hasAccountMetrics ? "已有手动账号数据" : "还没有账号表现数据"}</h3>
              <p>
                {hasAccountMetrics
                  ? "以下指标由用户手动填写，并非平台 API 返回。"
                  : "暂未接入小红书和画加 API，可通过编辑画像手动补充。"}
              </p>
            </div>
          </div>
        </div>
      </Card>
      <Card c="profilePerformanceCard">
        <div className="sectionHeadingRow">
          <div>
            <h2>账号表现概览</h2>
            <p>用于辅助判断账号阶段，所有数字都保留来源说明。</p>
          </div>
          <Chip>{hasAccountMetrics ? "用户手动填写" : "等待数据"}</Chip>
        </div>
        {hasAccountMetrics ? (
          <div className="manualMetricsGrid">
            {[
              ["小红书粉丝", xhsMetrics.followers],
              ["近 30 天发布", xhsMetrics.recentPosts],
              ["平均浏览", xhsMetrics.averageViews],
              ["平均收藏", xhsMetrics.averageFavorites],
              ["平均评论", xhsMetrics.averageComments],
              ["画加橱窗", huajiaMetrics.showcaseCount],
              ["画加橱窗收藏", huajiaMetrics.favorites],
              ["近 30 天完成订单", huajiaMetrics.completedOrders],
            ]
              .filter(([, value]) => String(value || "").trim())
              .map(([label, value]) => (
                <div key={label}>
                  <span>{label}</span>
                  <strong>{value}</strong>
                </div>
              ))}
          </div>
        ) : (
          <div className="performanceEmpty">
            <h3>还没有足够的账号表现数据</h3>
            <p>连接方式可用前，你可以先手动填写账号名称、粉丝、发布和橱窗数据。</p>
            <Button light onClick={beginProfile}>补充账号数据</Button>
          </div>
        )}
      </Card>
      <div className="profileUtilityRow">
        <button type="button" onClick={() => setPage("platforms")}>
          <Link2 size={18} />
          <span><b>平台信息</b><small>查看小红书与画加的连接状态</small></span>
          <ArrowRight size={17} />
        </button>
        <button type="button" onClick={() => setPage("candidate")}>
          <UserRound size={18} />
          <span><b>AI 候选画像</b><small>确认后才写入正式画像</small></span>
          <ArrowRight size={17} />
        </button>
      </div>
    </>
  );
}

function Chart({ period = "最近一个月" }) {
  return (
    <svg
      className="marketTrendChart"
      viewBox="0 0 700 190"
      role="img"
      aria-label={`画加重点业务${period}新增橱窗趋势`}
    >
      <title>{`画加重点业务${period}新增橱窗趋势`}</title>
      <desc>头像业务快速上行，宠物主题插画缓慢上行，场景插画轻微下降。</desc>
      <path
        className="chartGrid"
        d="M20 40H680M20 95H680M20 150H680"
        fill="none"
      />
      <polyline
        className="l1"
        fill="none"
        points="20,145 150,135 280,118 410,100 540,65 680,30"
      />
      <polyline
        className="l2"
        fill="none"
        points="20,150 150,130 280,120 410,104 540,94 680,70"
      />
      <polyline
        className="l3"
        fill="none"
        points="20,65 150,75 280,90 410,103 540,112 680,120"
      />
    </svg>
  );
}
function Market({ toast }) {
  const [page, setPage] = useState("overview"),
    [drawer, setDrawer] = useState(false),
    [timeMode, setTimeMode] = useState("week"),
    [period, setPeriod] = useState("最近一个月"),
    [refreshState, setRefreshState] = useState({ status: "idle" });
  const periodOptions = timeMode === "day"
    ? ["昨日", "近7日", "近15日", "近30日"]
    : ["本周", "最近4周", "最近6周", "最近3个月"];
  const refreshing = refreshState.status === "running";
  const latestData = refreshState.latest_data || {};
  const huajiaCount = latestData.huajia?.records || 0;
  const xhsCount = latestData.xiaohongshu?.records || 0;
  const hasCollectedData = huajiaCount + xhsCount > 0;
  const updateTime = refreshState.completed_at
    || latestData.huajia?.updated_at
    || latestData.xiaohongshu?.updated_at
    || refreshState.started_at;
  const formatUpdateTime = (value) => {
    if (!value) return "尚未从页面更新";
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return "已有本地数据";
    return `${date.toLocaleDateString("zh-CN")} ${date.toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" })}`;
  };
  useEffect(() => {
    let active = true;
    let timer;
    const readStatus = async () => {
      try {
        const data = await getAPI("/market/refresh/status");
        if (!active) return;
        setRefreshState(data);
        if (data.status === "running") timer = setTimeout(readStatus, 2500);
      } catch {
        if (active) setRefreshState((current) => ({ ...current, status: "unavailable" }));
      }
    };
    readStatus();
    return () => {
      active = false;
      clearTimeout(timer);
    };
  }, [refreshState.status]);
  const updateMarketData = async () => {
    try {
      const data = await postAPI("/market/refresh");
      setRefreshState(data);
      toast(data.status === "running" ? "正在更新公开市场数据" : data.message);
    } catch (error) {
      toast(error.message);
    }
  };
  const action = (
    <Button light onClick={() => setDrawer(true)}>
      <Database size={16} />
      数据来源与口径
    </Button>
  );
  const drawerNode = drawer && (
    <div className="drawerOverlay" onClick={() => setDrawer(false)}>
      <aside className="drawer" onClick={(e) => e.stopPropagation()}>
        <button
          className="close"
          aria-label="关闭数据详情"
          onClick={() => setDrawer(false)}
        >
          <X />
        </button>
        <h2>数据来源与口径</h2>
        <div className="sourceItem">
          <b>画加公开市场</b>
          <Chip green>{huajiaCount ? `${huajiaCount} 条样本` : "等待更新"}</Chip>
          <p>公开橱窗样本用于品类、价格、收藏和新增橱窗统计。</p>
        </div>
        <div className="sourceItem">
          <b>小红书公开趋势</b>
          <Chip>{xhsCount ? `${xhsCount} 条样本` : "部分字段不足"}</Chip>
          <p>公开推荐和关键词样本不以互动量直接代替真实需求。</p>
        </div>
        <Note>采集受限时保留上一次可用数据；页面不会补写不存在的数字。</Note>
        <Button
          disabled={refreshing}
          onClick={async () => {
            await updateMarketData();
            setDrawer(false);
          }}
        >
          <RefreshCw size={16} className={refreshing ? "refreshSpin" : ""} />
          {refreshing ? "更新中" : "重新获取"}
        </Button>
      </aside>
    </div>
  );
  if (page === "xhs")
    return (
      <>
        <Head
          title="小红书洞察"
          sub="大众话题、插画垂类与账号内容信号。"
          back={() => setPage("overview")}
          action={action}
        />
        <div className="grid3">
          {[
            ["近期曝光", "3,840", "近 30 天"],
            ["平均收藏率", "4.2%", "基于有数据笔记"],
            ["发布频率", "0.6 次/周", "不能单独判断流量下降"],
          ].map((x) => (
            <Card key={x[0]}>
              <small>{x[0]}</small>
              <h2>{x[1]}</h2>
              <p>{x[2]}</p>
            </Card>
          ))}
        </div>
        <Card>
          <h3>大众话题信号</h3>
          {["周末城市散步", "开学季桌面改造", "秋日氛围感配色"].map((x, i) => (
            <div className="signal" key={x}>
              <span>{i + 1}</span>
              <b>{x}</b>
              <Chip>{["关注上升", "高互动", "持续讨论"][i]}</Chip>
            </div>
          ))}
        </Card>
        {drawerNode}
      </>
    );
  if (page === "mhs")
    return (
      <>
        <Head
          title="画加洞察"
          sub="业务品类、价格、收藏与供给变化。"
          back={() => setPage("overview")}
          action={action}
        />
        <Card>
          <div className="row">
            <div>
              <h3>重点业务新增橱窗趋势</h3>
              <p>新增橱窗数量，不等同于真实成交需求。</p>
            </div>
            <select value={period} onChange={(e) => setPeriod(e.target.value)}>
              <option>最近一周</option>
              <option>最近一个月</option>
            </select>
          </div>
          <Chart period={period} />
          <div className="chartUpdated">最后更新时间：{formatUpdateTime(updateTime)}</div>
        </Card>
        <div className="table card">
          <b>业务</b>
          <b>新增橱窗</b>
          <b>价格带</b>
          <b>趋势</b>
          <span>头像业务</span>
          <span>+22</span>
          <span>¥80–260</span>
          <span>快速上行</span>
          <span>宠物主题插画</span>
          <span>+12</span>
          <span>¥100–600</span>
          <span>缓慢上行</span>
          <span>场景插画</span>
          <span>−4</span>
          <span>¥300–900</span>
          <span>轻微下降</span>
        </div>
        {drawerNode}
      </>
    );
  return (
    <>
      <Head
        title="市场洞察中心"
        sub="查看公开市场变化，不代表系统已经替你做出决策。"
        action={action}
      />
      <div className="mock">
        {hasCollectedData
          ? `当前已读取公开样本：画加 ${huajiaCount} 条，小红书 ${xhsCount} 条。样本不代表完整市场结论。`
          : "Mock 演示　以下趋势不代表真实市场结论。"}
      </div>
      <div className="filterBar">
        <div className="marketTimeControl">
          <div className="marketTimeHeading">
            <div>
              <b>时间范围</b>
              <span>{formatUpdateTime(updateTime)} 更新</span>
            </div>
            <div className="timeModeSwitch" aria-label="时间统计方式">
              {["day", "week"].map((mode) => (
                <button
                  type="button"
                  key={mode}
                  className={timeMode === mode ? "active" : ""}
                  onClick={() => {
                    setTimeMode(mode);
                    setPeriod(mode === "day" ? "近7日" : "最近6周");
                  }}
                >
                  {mode === "day" ? "按日" : "按周"}
                </button>
              ))}
            </div>
          </div>
          <div className="periodChoices" aria-label="选择时间范围">
            {periodOptions.map((option) => (
              <button type="button" key={option} className={period === option ? "active" : ""} onClick={() => setPeriod(option)}>
                {option}
              </button>
            ))}
          </div>
        </div>
        <Button onClick={updateMarketData} disabled={refreshing}>
          <RefreshCw size={16} className={refreshing ? "refreshSpin" : ""} />
          {refreshing ? "更新中" : "更新数据"}
        </Button>
      </div>
      <div className="market">
        <Card>
          <h3>画加重点业务新增橱窗趋势</h3>
          <p>纵轴：新增橱窗数（个） · 横轴：周</p>
          <Chart period={period} />
          <div className="legend">
            <span className="orangeDot">头像业务</span>
            <span className="greenDot">宠物主题插画</span>
            <span className="grayDot">场景插画</span>
          </div>
          <div className="chartUpdated">最后更新时间：{formatUpdateTime(updateTime)}</div>
          <Button light onClick={() => setPage("mhs")}>
            查看画加详情
          </Button>
        </Card>
        <Card>
          <small>本周市场观察</small>
          <h2>头像业务增速最快</h2>
          <p>本周新增橱窗较上周增长约 22%；宠物主题插画保持缓慢上行。</p>
        </Card>
      </div>
      <div className="grid2">
        <Card>
          <h3>小红书大众热门话题</h3>
          <p>
            周末城市散步　<Chip>关注上升</Chip>
          </p>
          <p>
            开学季桌面改造　<Chip>高互动</Chip>
          </p>
          <p>
            秋日氛围感配色　<Chip>持续讨论</Chip>
          </p>
          <Button light onClick={() => setPage("xhs")}>
            查看小红书详情
          </Button>
        </Card>
        <Card>
          <h3>画加细分业务趋势</h3>
          <p>宠物主题插画　+12</p>
          <p>头像业务　+22</p>
          <p>场景插画　−4</p>
        </Card>
      </div>
      {drawerNode}
    </>
  );
}

function Confirm({ item, close, done }) {
  return (
    <div className="overlay">
      <Card c="modal">
        <button className="close" aria-label="关闭方向确认" onClick={close}>
          <X />
        </button>
        <Chip green>等待确认</Chip>
        <h2>确认本轮商业方向</h2>
        <p>你选择了“{item.name}”。本轮不增加当前接单强度。</p>
        <Note>当前产能为可接单，预计投入每周 3 小时运营时间。</Note>
        <div className="right">
          <Button light onClick={close}>
            返回比较
          </Button>
          <Button onClick={done}>确认并生成方案</Button>
        </div>
      </Card>
    </div>
  );
}
function Decision({ go, toast }) {
  const [page, setPage] = useState("list"),
    [target, setTarget] = useState("提高自然流量"),
    [selected, setSelected] = useState(OPS[0]),
    [confirm, setConfirm] = useState(false),
    [aiExplanation, setAiExplanation] = useState(null),
    [aiPending, setAiPending] = useState(false);
  const explain = async () => {
    setAiPending(true);
    try {
      const data = await postAI("/ai/opportunity-explanation", {
        user_id: currentUserId(),
        candidate: selected,
      });
      setAiExplanation(data);
      toast("AI 机会解释已生成");
    } catch (error) {
      toast(error.message);
    } finally {
      setAiPending(false);
    }
  };
  const analyze = () => {
    setPage("loading");
    setTimeout(() => setPage("list"), 800);
  };
  if (page === "target")
    return (
      <>
        <Head
          title="确认本轮经营目标"
          sub="目标影响机会排序，但不会覆盖长期画像。"
          back={() => setPage("list")}
        />
        <Card>
          <div className="options compactOptions">
            {[
              "提高自然流量",
              "吸引潜在客户",
              "提高咨询量",
              "提高成交",
              "测试新业务方向",
            ].map((x) => (
              <button
                className={target === x ? "selected" : ""}
                onClick={() => setTarget(x)}
                key={x}
              >
                <span>
                  <b>{x}</b>
                </span>
                <i>{target === x ? <Check size={15} /> : null}</i>
              </button>
            ))}
          </div>
          <label>
            自定义目标
            <input
              placeholder="写下本轮具体目标"
              onChange={(e) => e.target.value && setTarget(e.target.value)}
            />
          </label>
          <div className="right">
            <Button onClick={analyze}>确认并重新分析</Button>
          </div>
        </Card>
      </>
    );
  if (page === "loading")
    return (
      <div className="loadingState">
        <RefreshCw className="spin" />
        <h2>正在重新整理商业机会</h2>
        <p>检查画像、市场事实、业务规则与证据版本。</p>
      </div>
    );
  if (page === "detail")
    return (
      <>
        <Head
          title={selected.name}
          sub="查看评分依据、反向因素和缺失信息。"
          back={() => setPage("list")}
        />
        <Card c="scoreDetail">
          <strong>{selected.score}</strong>
          <div>
            <Chip green>{selected.level}</Chip>
            <h2>Opportunity Score</h2>
            <p>画像匹配 30 · 市场信号 18 · 产能适配 16 · 执行成本 12</p>
          </div>
        </Card>
        <div className="grid3">
          <Card>
            <h3>支持证据</h3>
            {selected.support.map((x) => (
              <p className="evidence yes" key={x}>
                <Check size={15} />
                {x}
              </p>
            ))}
          </Card>
          <Card>
            <h3>反向因素</h3>
            {selected.risk.map((x) => (
              <p className="evidence no" key={x}>
                <X size={15} />
                {x}
              </p>
            ))}
          </Card>
          <Card>
            <h3>缺失信息</h3>
            {selected.missing.map((x) => (
              <p key={x}>{x}</p>
            ))}
            <p>置信度：{selected.confidence}</p>
          </Card>
        </div>
        <Card>
          <h3>最小验证计划</h3>
          <p>用一次创作过程图文测试收藏与咨询，一周后回填结果。</p>
        </Card>
        {aiExplanation && (
          <Card>
            <small>AI 综合解释</small>
            <h3>{aiExplanation.summary}</h3>
            <p>
              <b>下一步：</b>
              {aiExplanation.next_actions.join("；")}
            </p>
            <p className="fineprint">
              分数与等级仍来自规则系统，AI 未参与计算。
            </p>
          </Card>
        )}
        <div className="right">
          <Button light onClick={explain} disabled={aiPending}>
            {aiPending ? "AI 解释中…" : "AI 解释这个机会"}
          </Button>
          <Button light onClick={() => toast("已标记为不适合")}>
            标记不适合
          </Button>
          <Button onClick={() => setConfirm(true)}>选择该方向</Button>
        </div>
        {confirm && (
          <Confirm
            item={selected}
            close={() => setConfirm(false)}
            done={() => go("plan")}
          />
        )}
      </>
    );
  return (
    <>
      <Head
        title="商业机会决策中心"
        sub="比较评分依据和缺失信息，再由你选择本轮方向。"
        action={
          <Button light onClick={() => setPage("target")}>
            修改目标
          </Button>
        }
      />
      <Card c="orange row">
        <div>
          <small>本轮目标</small>
          <h3>{target}</h3>
        </div>
        <Button light onClick={analyze}>
          <RefreshCw size={15} />
          重新分析
        </Button>
      </Card>
      {OPS.map((x, i) => (
        <Card c={"op " + (!i ? "chosen" : "")} key={x.name}>
          <div className="opScore">
            <strong>{x.score}</strong>
            <small>机会评分</small>
          </div>
          <div>
            <h3>
              {x.name}　<Chip green={!i}>{x.level}</Chip>
            </h3>
            <p>支持：{x.support[0]}</p>
            <p className="risk">反向因素：{x.risk[0]}</p>
          </div>
          <div className="buttonStack">
            <Button
              light
              onClick={() => {
                setSelected(x);
                setPage("detail");
              }}
            >
              查看完整证据
            </Button>
            {!i && (
              <Button
                onClick={() => {
                  setSelected(x);
                  setConfirm(true);
                }}
              >
                选择此方向
              </Button>
            )}
          </div>
        </Card>
      ))}
      {confirm && (
        <Confirm
          item={selected}
          close={() => setConfirm(false)}
          done={() => go("plan")}
        />
      )}
    </>
  );
}

function DecisionScored({ go, toast, profile, setProfile }) {
  const [page, setPage] = useState("list"),
    [target, setTarget] = useState("提高自然流量"),
    [items, setItems] = useState([]),
    [selected, setSelected] = useState(null),
    [confirm, setConfirm] = useState(false),
    [meta, setMeta] = useState(null),
    [error, setError] = useState(""),
    [aiExplanation, setAiExplanation] = useState(null),
    [aiPending, setAiPending] = useState(false),
    [loading, setLoading] = useState(true);
  const loadScores = async () => {
    setLoading(true);
    setError("");
    try {
      const data = await getAPI("/opportunities/score");
      setItems(data.opportunities || []);
      setSelected(
        (current) =>
          (data.opportunities || []).find(
            (x) => x.candidate_id === current?.candidate_id,
          ) ||
          data.opportunities?.[0] ||
          null,
      );
      setMeta(data);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };
  useEffect(() => {
    loadScores();
  }, []);
  const explain = async () => {
    if (!selected) return;
    setAiPending(true);
    try {
      const data = await postAI("/ai/opportunity-explanation", {
        user_id: currentUserId(),
        candidate: selected,
      });
      setAiExplanation(data);
      toast("AI 机会解释已生成");
    } catch (e) {
      toast(e.message);
    } finally {
      setAiPending(false);
    }
  };
  const choose = async () => {
    localStorage.setItem(
      accountStorageKey("ama-selected-opportunity"),
      JSON.stringify(selected),
    );
    try {
      await postAI("/memory/" + currentUserId() + "/analyses", {
        analysis_type: "opportunity",
        result_id: `opportunity-${selected.candidate_id}`,
        result: selected,
      });
    } catch (error) {
      toast(`方向已保存在当前设备；长期记录失败：${error.message}`);
    }
    setConfirm(false);
    go("plan");
  };
  const confirmTarget = async () => {
    try {
      const nextProfile = { ...profile, goal: target };
      const data = await putAPI(
        "/workflow/profile/" + currentUserId(),
        profilePayload(nextProfile),
      );
      setProfile({ ...nextProfile, ...(data.ui_profile || {}) });
      setPage("list");
      await loadScores();
    } catch (error) {
      toast(error.message);
    }
  };
  if (page === "target")
    return (
      <>
        <Head
          title="确认本轮经营目标"
          sub="目标影响机会排序，但不会覆盖长期画像。"
          back={() => setPage("list")}
        />
        <Card>
          <div className="options compactOptions">
            {[
              "提高自然流量",
              "吸引潜在客户",
              "提高咨询量",
              "提高成交",
              "测试新业务方向",
            ].map((x) => (
              <button
                className={target === x ? "selected" : ""}
                onClick={() => setTarget(x)}
                key={x}
              >
                <span>
                  <b>{x}</b>
                </span>
                <i>{target === x ? <Check size={15} /> : null}</i>
              </button>
            ))}
          </div>
          <label>
            自定义目标
            <input
              placeholder="写下本轮具体目标"
              onChange={(e) => e.target.value && setTarget(e.target.value)}
            />
          </label>
          <div className="right">
              <Button onClick={confirmTarget}>
                确认并重新分析
              </Button>
          </div>
        </Card>
      </>
    );
  if (loading)
    return (
      <div className="loadingState">
        <RefreshCw className="spin" />
        <h2>规则系统正在计算商业机会</h2>
        <p>读取已确认画像、画加测试市场事实与小红书测试趋势。</p>
      </div>
    );
  if (error)
    return (
      <>
        <Head title="商业机会决策中心" sub="评分服务暂时不可用。" />
        <Card>
          <h3>无法取得规则评分</h3>
          <p>{error}</p>
          <Button onClick={loadScores}>重新获取</Button>
        </Card>
      </>
    );
  if (page === "detail" && selected)
    return (
      <>
        <Head
          title={selected.name}
          sub="查看规则评分、证据和缺失信息。"
          back={() => setPage("list")}
        />
        <Note>
          Opportunity Score 由 {selected.rule_version} 固定规则计算并锁定；LLM
          只能解释。
        </Note>
        <Card c="scoreDetail">
          <strong>{selected.score}</strong>
          <div>
            <Chip green>{selected.level}</Chip>
            <h2>Opportunity Score</h2>
            <p>
              {selected.components
                .filter((x) => x.score !== null)
                .map((x) => `${x.label} ${x.score}`)
                .join(" · ")}
            </p>
          </div>
        </Card>
        <div className="grid3">
          <Card>
            <h3>支持因素</h3>
            {selected.support.length ? (
              selected.support.map((x) => (
                <p className="evidence yes" key={x}>
                  <Check size={15} />
                  {x}
                </p>
              ))
            ) : (
              <p>暂无达到强支持阈值的分项</p>
            )}
          </Card>
          <Card>
            <h3>反向因素</h3>
            {selected.risk.length ? (
              selected.risk.map((x) => (
                <p className="evidence no" key={x}>
                  <X size={15} />
                  {x}
                </p>
              ))
            ) : (
              <p>暂无低于阈值的分项</p>
            )}
          </Card>
          <Card>
            <h3>缺失信息</h3>
            {selected.missing.length ? (
              selected.missing.map((x) => <p key={x}>{x}</p>)
            ) : (
              <p>评分必需字段完整</p>
            )}
            <p>置信度：{selected.confidence}</p>
          </Card>
        </div>
        <Card>
          <h3>评分审计信息</h3>
          <p>
            市场证据：{selected.evidence_ids.market.join("、")}　趋势证据：
            {selected.evidence_ids.trends.join("、") || "无匹配"}
          </p>
          <p>
            证据时间：{selected.evidence_as_of}　规则版本：
            {selected.rule_version}
          </p>
        </Card>
        {aiExplanation && (
          <Card>
            <small>AI 综合解释</small>
            <h3>{aiExplanation.summary}</h3>
            <p>
              <b>下一步：</b>
              {aiExplanation.next_actions.join("；")}
            </p>
            <p className="fineprint">分数与等级来自规则系统，AI 未参与计算。</p>
          </Card>
        )}
        <div className="right">
          <Button light onClick={explain} disabled={aiPending}>
            {aiPending ? "AI 解释中…" : "AI 解释这个机会"}
          </Button>
          <Button light onClick={() => toast("已标记为不适合")}>
            标记不适合
          </Button>
          <Button onClick={() => setConfirm(true)}>选择该方向</Button>
        </div>
        {confirm && (
          <Confirm
            item={selected}
            close={() => setConfirm(false)}
            done={choose}
          />
        )}
      </>
    );
  return (
    <>
      <Head
        title="商业机会决策中心"
        sub="比较规则评分依据和缺失信息，再由你选择本轮方向。"
        action={
          <Button light onClick={() => setPage("target")}>
            修改目标
          </Button>
        }
      />
      <Card c="orange row">
        <div>
          <small>本轮目标</small>
          <h3>{target}</h3>
        </div>
        <Button light onClick={loadScores}>
          <RefreshCw size={15} />
          重新分析
        </Button>
      </Card>
      <Note>{meta?.data_notice} 评分由规则引擎计算，AI 仅负责解释。</Note>
      {items.map((x, i) => (
        <Card c={"op " + (!i ? "chosen" : "")} key={x.candidate_id}>
          <div className="opScore">
            <strong>{x.score}</strong>
            <small>机会评分</small>
          </div>
          <div>
            <h3>
              {x.name}　<Chip green={!i}>{x.level}</Chip>
            </h3>
            <p>支持：{x.support[0] || "暂无强支持分项"}</p>
            <p className="risk">反向因素：{x.risk[0] || "暂无低分项"}</p>
            <small>
              置信度 {x.confidence} · {x.rule_version}
            </small>
          </div>
          <div className="buttonStack">
            <Button
              light
              onClick={() => {
                setSelected(x);
                setAiExplanation(null);
                setPage("detail");
              }}
            >
              查看完整证据
            </Button>
            {!i && (
              <Button
                onClick={() => {
                  setSelected(x);
                  setConfirm(true);
                }}
              >
                选择此方向
              </Button>
            )}
          </div>
        </Card>
      ))}
      {confirm && selected && (
        <Confirm
          item={selected}
          close={() => setConfirm(false)}
          done={choose}
        />
      )}
    </>
  );
}

function Steps({ s }) {
  return (
    <div className="planSteps">
      {["营销策略", "内容形式", "对应方案", "发布"].map((x, i) => (
        <span className={i < s ? "done" : i === s ? "now" : ""} key={x}>
          <i>{i < s ? <Check size={10} /> : null}</i>
          {x}
        </span>
      ))}
    </div>
  );
}

const DETAILED_VIDEO_SCRIPT = `总时长：30 秒

00:00–00:04（4 秒）
展示内容：客户提供的宠物照片与成品挂件快速对照
口播：一张普通的宠物照片，怎样变成一枚可以随身携带的水彩挂件？

00:04–00:09（5 秒）
展示内容：圈出照片中最有辨识度的神态、花纹和配色
口播：我会先保留它最特别的表情和花纹，再决定画面的取舍。

00:09–00:18（9 秒）
展示内容：钢笔草图、水彩铺色与局部刻画过程
口播：从钢笔勾线到水彩上色，每一步都围绕原本的性格和神态来画。

00:18–00:26（8 秒）
展示内容：双面挂件正反面、边缘和水彩质感细节
口播：完成后会保留手绘的笔触，也能从正反两面看到不同的小细节。

00:26–00:30（4 秒）
展示内容：成品佩戴或摆放场景，画面出现咨询提示
口播：如果你也想把毛孩子画成专属纪念，欢迎告诉我它的故事。`;

const MARKETING_GOALS = {
  流量增长: {
    summary: "用可搜索、可持续的内容扩大自然曝光",
    position: "用可搜索的宠物手绘过程扩大自然曝光",
    focus: "稳定呈现题材关键词、成品差异与创作过程",
    title: "一张宠物照片，是怎么变成水彩手绘挂件的？",
    body: "从照片里的神态和花纹开始，我用钢笔勾线、水彩铺色，再完成正反面的细节。记录这次从照片到成品的完整过程，也欢迎收藏你最喜欢的一步。",
  },
  吸引潜在客源: {
    summary: "让有明确需求的人更容易理解并发起咨询",
    position: "用真实案例与定制流程降低潜在客户的咨询门槛",
    focus: "突出适合谁、如何沟通、最终会获得什么",
    title: "想把毛孩子画成挂件，委托前可以先看这 3 步",
    body: "你只需要提供清晰照片和希望保留的特点，我会先确认神态与配色，再依次完成草图、上色和成品确认。想了解自己的照片是否适合，可以先告诉我你的需求。",
  },
  增加客单: {
    summary: "解释高价值方案的差异，支持更完整的委托",
    position: "用成品规格、纪念价值与场景完整度说明高客单方案",
    focus: "突出复杂度、服务范围、交付内容与价值差异",
    title: "从头像到场景纪念插画，不同方案差在哪里？",
    body: "头像方案聚焦神态和辨识度；场景插画会加入环境、故事与更多细节，也需要更长的创作周期。选择时可以从用途、画面完整度和预算三个方面判断。",
  },
};

function formatVideoScript(nextContent, fallback) {
  const script = nextContent.video_script;
  if (!Array.isArray(script) || !script.length) return fallback;
  if (typeof script[0] === "string") {
    const total = nextContent.total_duration_seconds;
    return `${total ? `总时长：${total} 秒\n\n` : ""}${script.join("\n")}`;
  }
  const total =
    nextContent.total_duration_seconds ||
    script.reduce((sum, item) => sum + Number(item.duration_seconds || 0), 0);
  const segments = script.map((item, index) => {
    const range =
      item.start_time && item.end_time
        ? `${item.start_time}–${item.end_time}`
        : `第 ${index + 1} 段`;
    const duration = item.duration_seconds ? `（${item.duration_seconds} 秒）` : "";
    return `${range}${duration}\n展示内容：${item.visual || item.content || "待补充"}\n口播：${item.voiceover || item.narration || "待补充"}`;
  });
  return `${total ? `总时长：${total} 秒\n\n` : ""}${segments.join("\n\n")}`;
}

function Plan({ go, toast }) {
  const [selectedOpportunity] = useState(() => {
      try {
        return (
          JSON.parse(
            localStorage.getItem(accountStorageKey("ama-selected-opportunity")),
          ) || OPS[0]
        );
      } catch {
        return OPS[0];
      }
    }),
    [s, setS] = useStored("ama-plan-step", 0),
    [fmt, setFmt] = useStored("ama-plan-format", "image"),
    [marketingGoal, setMarketingGoal] = useStored(
      "ama-marketing-goal",
      "流量增长",
    ),
    [strategy, setStrategy] = useStored("ama-strategy", {
      position: "用传统手绘记录宠物与兽设的独特性",
      audience: "宠物用户、兽设 OC 客户",
      rhythm: "每周一个重点内容",
    }),
    [content, setContent] = useStored("ama-content", {
      title: "给毛孩子留下一份手绘纪念",
      body: "从客户提供的照片开始，我先保留它最有辨识度的神态，再用水彩和钢笔完成这枚双面挂件……",
      video: DETAILED_VIDEO_SCRIPT,
    }),
    [aiPending, setAiPending] = useState(false);
  useEffect(() => {
    if (!content.video?.includes("总时长：")) {
      setContent((current) => ({ ...current, video: DETAILED_VIDEO_SCRIPT }));
    }
  }, []);
  const generatePlan = async () => {
    setAiPending(true);
    try {
      const data = await postAI("/ai/marketing-plan", {
        user_id: currentUserId(),
        candidate: selectedOpportunity,
        marketing_goal: marketingGoal,
        content_format: fmt === "image" ? "image_text" : "video",
        current_draft: { marketing_goal: marketingGoal, strategy, content },
      });
      const nextStrategy = data.strategy || {};
      setStrategy({
        position: nextStrategy.positioning || strategy.position,
        audience: nextStrategy.audience || strategy.audience,
        rhythm: nextStrategy.rhythm || strategy.rhythm,
        pillars: nextStrategy.content_pillars || [],
        sellingPoints: nextStrategy.selling_points || [],
      });
      const nextContent = data.content || {};
      if (fmt === "image")
        setContent({
          ...content,
          title: (nextContent.title_options || [])[0] || content.title,
          body: nextContent.body || content.body,
          imageSequence: nextContent.image_sequence || content.imageSequence,
          visualNotes: nextContent.visual_notes || "",
        });
      else
        setContent({
          ...content,
          video: formatVideoScript(nextContent, content.video),
          hook: nextContent.hook || "",
          caption: nextContent.caption || "",
        });
      toast("AI 方案草稿已生成");
    } catch (error) {
      toast(error.message);
    } finally {
      setAiPending(false);
    }
  };
  const copy = async () => {
    await navigator.clipboard?.writeText(
      fmt === "image"
        ? `标题：${content.title}\n\n正文：${content.body}`
        : content.video,
    );
    toast("文字已复制");
  };
  const finishPlan = async () => {
    try {
      await postAI("/memory/" + currentUserId() + "/analyses", {
        analysis_type: "marketing_plan",
        result_id: `plan-${selectedOpportunity.candidate_id}-${fmt}-${marketingGoal}`,
        result: {
          candidate: selectedOpportunity,
          content_format: fmt === "image" ? "image_text" : "video",
          marketing_goal: marketingGoal,
          strategy,
          content,
        },
      });
      toast("方案已确认并写入历史记录");
      setS(0);
      go("history");
    } catch (error) {
      toast(error.message);
    }
  };
  return (
    <>
      <Head
        title="营销与内容方案中心"
        sub="把已确认方向整理成可编辑、可执行的文字方案。"
        action={
          <Button light onClick={() => go("decision")}>
            返回更换方向
          </Button>
        }
      />
      <Card c="orange row">
        <b>{selectedOpportunity.name}</b>
        <span>机会评分 {selectedOpportunity.score} · AI 可编辑方案</span>
      </Card>
      <Steps s={s} />
      {s === 0 && (
        <>
          <div className="grid2">
            <Card>
              <small>账号定位</small>
              <h2>{strategy.position}</h2>
              <p>突出水彩质感、手作温度与可沟通的定制过程。</p>
            </Card>
            <Card>
              <small>目标客户</small>
              <h3>{strategy.audience}</h3>
              <dl className="audienceFacts">
                <div>
                  <dt>主要需求</dt>
                  <dd>宠物纪念、兽设个性表达</dd>
                </div>
                <div>
                  <dt>关注信息</dt>
                  <dd>成品风格、定制流程、价格与交付</dd>
                </div>
              </dl>
            </Card>
          </div>
          <div className="planGoalHeading">
            <h3>选择本轮营销目的</h3>
            <p>单选。后续策略、图文或视频脚本都会围绕这个目的生成。</p>
          </div>
          <div className="planGoalChoices" role="radiogroup" aria-label="本轮营销目的">
            {Object.entries(MARKETING_GOALS).map(([name, goal]) => (
              <button
                type="button"
                role="radio"
                aria-checked={marketingGoal === name}
                className={marketingGoal === name ? "selected" : ""}
                key={name}
                onClick={() => {
                  setMarketingGoal(name);
                  setStrategy((current) => ({
                    ...current,
                    position: goal.position,
                  }));
                  setContent((current) => ({
                    ...current,
                    title: goal.title,
                    body: goal.body,
                  }));
                }}
              >
                <span>
                  <h3>{name}</h3>
                  <p>{goal.summary}</p>
                </span>
                <i>{marketingGoal === name ? <Check size={13} /> : null}</i>
              </button>
            ))}
          </div>
          <div className="right">
            <Button light onClick={generatePlan} disabled={aiPending}>
              {aiPending ? "AI 生成中…" : "AI 生成策略"}
            </Button>
          </div>
        </>
      )}
      {s === 1 && (
        <>
          <div className="selectedGoalNote">
            <b>本轮目的：{marketingGoal}</b>
            <span>{MARKETING_GOALS[marketingGoal].focus}</span>
          </div>
          <div className="formats">
          {[
            ["image", FileText, "图文 · 图序与文案"],
            ["video", PenLine, "视频 · 文字脚本"],
          ].map(([id, I, t]) => (
            <button
              className={fmt === id ? "selected" : ""}
              onClick={() => setFmt(id)}
              key={id}
            >
              <I />
              <h3>{t}</h3>
              <p>二选一，只进入对应方案。</p>
            </button>
          ))}
          </div>
        </>
      )}
      {s === 2 && (
        <Card>
          <h2>{fmt === "image" ? "小红书图文方案" : "视频文字脚本"}</h2>
          <div className="selectedGoalNote compact">
            <b>对应目的：{marketingGoal}</b>
            <span>{MARKETING_GOALS[marketingGoal].focus}</span>
          </div>
          {fmt === "image" ? (
            <>
              <label>
                标题
                <input
                  value={content.title}
                  onChange={(e) =>
                    setContent({ ...content, title: e.target.value })
                  }
                />
              </label>
              <label>
                正文
                <textarea
                  value={content.body}
                  onChange={(e) =>
                    setContent({ ...content, body: e.target.value })
                  }
                />
              </label>
              <h3>图序建议</h3>
              <div className="copy">
                {(
                  content.imageSequence || [
                    "成品",
                    "局部细节",
                    "草图过程",
                    "使用场景",
                  ]
                ).join(" → ")}
              </div>
              <small>产品不会生成图片，图序仅作为拍摄和排版提示。</small>
            </>
          ) : (
            <label>
              视频文字脚本
              <textarea
                className="scriptArea"
                value={content.video}
                onChange={(e) =>
                  setContent({ ...content, video: e.target.value })
                }
              />
            </label>
          )}
          <div className="right">
            <Button light onClick={() => toast("方案草稿已保存在当前设备")}>
              保存草稿
            </Button>
            <Button light onClick={generatePlan} disabled={aiPending}>
              {aiPending ? "AI 生成中…" : "AI 重新生成"}
            </Button>
          </div>
        </Card>
      )}
      {s === 3 && (
        <Card>
          <Chip green>方案已确认</Chip>
          <h2>{fmt === "image" ? "图文发布内容" : "视频发布内容"}</h2>
          <h3>营销策略</h3>
          <p>
            本轮目的：{marketingGoal}。{strategy.position}。目标客户：{strategy.audience}。
          </p>
          <div className="copy">
            {fmt === "image"
              ? `标题：${content.title}\n\n正文：${content.body}`
              : content.video}
          </div>
          {fmt === "image" && (
            <>
              <h3>图序建议</h3>
              <p>
                {(
                  content.imageSequence || [
                    "成品",
                    "局部细节",
                    "草图过程",
                    "使用场景",
                  ]
                ).join(" → ")}
              </p>
              <small>图序仅供查看，不进入复制内容。</small>
            </>
          )}
          <div className="buttonRow topGap">
            <Button onClick={copy}>
              <Clipboard size={16} />
              一键复制文字
            </Button>
          </div>
        </Card>
      )}
      <div className="right">
        <Button light onClick={() => (s ? setS(s - 1) : go("decision"))}>
          返回
        </Button>
        <Button onClick={() => (s === 3 ? finishPlan() : setS(s + 1))}>
          {["确认策略", "确认形式", "确认方案", "完成并发布"][s]}
        </Button>
      </div>
    </>
  );
}

function History({ go, profile, setProfile, toast }) {
  const [selectedOpportunity] = useState(() => {
      try {
        return (
          JSON.parse(
            localStorage.getItem(accountStorageKey("ama-selected-opportunity")),
          ) || OPS[0]
        );
      } catch {
        return OPS[0];
      }
    }),
    [page, setPage] = useState("list"),
    [modal, setModal] = useState(false),
    [addRecordOpen, setAddRecordOpen] = useState(false),
    [manualRecords, setManualRecords] = useStored("ama-manual-records", []),
    [timeFilter, setTimeFilter] = useState("全部时间"),
    [platformFilter, setPlatformFilter] = useState("全部平台"),
    [statusFilter, setStatusFilter] = useState("全部状态"),
    [typeFilter, setTypeFilter] = useState("全部类型"),
    [activeRecord, setActiveRecord] = useState(null),
    [resultType, setResultType] = useStored("ama-result-type", "笔记"),
    [publishedAt, setPublishedAt] = useStored("ama-result-published-at", ""),
    [businessDraft, setBusinessDraft] = useState(createBusinessDraft()),
    [recordDraft, setRecordDraft] = useState({
      title: "",
      type: "笔记",
      platform: "小红书",
      publishedAt: "",
      exposure: "",
      views: "",
      favorites: "",
      comments: "",
      conversions: "",
      note: "",
    }),
    [capacity, setCapacity] = useState(profile.status),
    [metrics, setMetrics] = useStored("ama-metrics", {
      曝光: 2860,
      浏览: 2860,
      收藏: 31,
      评论: 3,
      成交: 1,
      备注: "",
    }),
    [review, setReview] = useState(null),
    [aiPending, setAiPending] = useState(false);
  const builtInRecords = [
    { id: "record-1", title: "动物大头手绘挂件", platform: "小红书", type: "笔记", period: "本周", status: "待回填" },
    { id: "record-2", title: "带场景龙设插图", platform: "画加", type: "业务", period: "本月", status: "已复盘" },
    { id: "record-3", title: "鹦鹉双面挂件", platform: "小红书", type: "笔记", period: "本月", status: "已复盘" },
  ];
  const records = [...manualRecords, ...builtInRecords].filter((record) => {
    const timeMatches = timeFilter === "全部时间" || record.period === timeFilter;
    const platformMatches = platformFilter === "全部平台" || record.platform === platformFilter;
    const statusMatches = statusFilter === "全部状态" || record.status === statusFilter;
    const typeMatches = typeFilter === "全部类型" || record.type === typeFilter;
    return timeMatches && platformMatches && statusMatches && typeMatches;
  });
  const saveManualRecord = (event) => {
    event.preventDefault();
    if (!recordDraft.title.trim() || !recordDraft.publishedAt) {
      toast("请填写内容名称和发布时间");
      return;
    }
    setManualRecords((current) => [
      {
        ...recordDraft,
        id: `manual-${Date.now()}`,
        title: recordDraft.title.trim(),
        period: "本周",
        status: "待回填",
        source: "用户自行发布",
      },
      ...current,
    ]);
    setRecordDraft({
      title: "",
      type: "笔记",
      platform: "小红书",
      publishedAt: "",
      exposure: "",
      views: "",
      favorites: "",
      comments: "",
      conversions: "",
      note: "",
    });
    setAddRecordOpen(false);
    toast("记录已添加");
  };
  const generateReview = async () => {
    setAiPending(true);
    try {
      const data = await postAI("/ai/outcome-review", {
        user_id: currentUserId(),
        goal: profile.goal,
        direction: activeRecord?.title || selectedOpportunity.name,
        metrics: {
          类型: resultType,
          发布时间: publishedAt,
          ...metrics,
        },
      });
      setReview(data);
      toast("AI 复盘已生成");
    } catch (error) {
      toast(error.message);
    } finally {
      setAiPending(false);
    }
  };
  const submitOutcome = async () => {
    if (!publishedAt) {
      toast("请先填写发布时间");
      return;
    }
    const reportedMetrics = resultType === "业务"
      ? {
          views: Number(metrics.浏览 || 0),
          favorites: Number(metrics.收藏 || 0),
          conversions: Number(metrics.成交 || 0),
        }
      : {
          exposure: Number(metrics.曝光 || 0),
          favorites: Number(metrics.收藏 || 0),
          comments: Number(metrics.评论 || 0),
        };
    try {
      await postAI("/memory/" + currentUserId() + "/outcomes", {
        direction: activeRecord?.title || selectedOpportunity.name,
        platform: resultType === "业务" ? "huajia" : "xiaohongshu",
        metrics: {
          ...reportedMetrics,
          published_at: publishedAt,
        },
        capacity_status:
          { 可接单: "available", 交付中: "near_limit", 满载: "full", 暂停: "full" }[
            capacity
          ] || "unknown",
        source: "user_reported",
        observed_at: new Date().toISOString(),
        note: metrics.备注 || null,
      });
      toast("真实结果已写入长期记忆");
      setPage("review");
    } catch (error) {
      toast(error.message);
    }
  };
  const updateSyncedBusiness = (field, value) => {
    setBusinessDraft((current) => ({ ...current, [field]: value }));
  };
  const openBusinessSync = () => {
    setBusinessDraft({
      ...createBusinessDraft(),
      name: activeRecord?.title || selectedOpportunity.name || "",
      showcaseType: (activeRecord?.title || selectedOpportunity.name)?.includes("头像") ? "头像" : "",
      finishedContent: activeRecord?.title || selectedOpportunity.name || "",
      excludedType: profile.boundaries || "",
    });
    setPage("business-sync");
  };
  const saveBusinessToProfile = async (event) => {
    event.preventDefault();
    const required = [
      ["name", "业务名称"],
      ["businessType", "业务类型"],
      ["showcaseType", "橱窗类型"],
      ["finishedContent", "成稿内容"],
      ["excludedType", "不接类型"],
    ];
    const missing = required.find(([key]) => !String(businessDraft[key] || "").trim());
    if (missing) {
      toast(`请填写${missing[1]}`);
      return;
    }
    if (businessDraft.showcaseType === "其他" && !businessDraft.showcaseTypeOther.trim()) {
      toast("请填写其他橱窗类型");
      return;
    }
    const nextProfile = {
      ...profile,
      existingBusinesses: [...(profile.existingBusinesses || []), businessDraft],
    };
    setProfile(nextProfile);
    try {
      await putAPI("/workflow/profile/" + currentUserId(), profilePayload(nextProfile));
      toast("业务详情已同步至用户画像");
    } catch {
      toast("业务已保存在当前设备，后端同步将在服务恢复后重试");
    }
    setPage("entry");
  };
  if (page === "business-sync")
    return (
      <>
        <Head
          title="补充业务详情"
          sub="确认后，这项业务会加入用户画像中的现有业务。"
          back={() => setPage("entry")}
        />
        <Card c="businessSyncCard">
          <Note>
            业务名称、业务类型、橱窗类型、不接类型和成稿内容为必填；其余为选填。填写越详细，分析越准确。
          </Note>
          <form onSubmit={saveBusinessToProfile}>
            <div className="form two businessSyncForm">
              <label>
                业务名称 *
                <input value={businessDraft.name} onChange={(event) => updateSyncedBusiness("name", event.target.value)} />
              </label>
              <label>
                业务类型 *
                <select value={businessDraft.businessType} onChange={(event) => updateSyncedBusiness("businessType", event.target.value)}>
                  <option value="">请选择业务类型</option>
                  {["邀请业务", "普通橱窗", "快速橱窗", "24小时特快橱窗"].map((option) => <option key={option}>{option}</option>)}
                </select>
              </label>
              <label>
                工期范围
                <input value={businessDraft.durationRange} onChange={(event) => updateSyncedBusiness("durationRange", event.target.value)} placeholder="例如：3–7 天" />
              </label>
              <label>
                橱窗类型 *
                <select value={businessDraft.showcaseType} onChange={(event) => updateSyncedBusiness("showcaseType", event.target.value)}>
                  <option value="">请选择橱窗类型</option>
                  {["头像", "Q版全身", "半身像", "立绘", "组合页", "服设", "其他"].map((option) => <option key={option}>{option}</option>)}
                </select>
              </label>
              {businessDraft.showcaseType === "其他" && (
                <label className="fullField">
                  其他橱窗类型 *
                  <input value={businessDraft.showcaseTypeOther} onChange={(event) => updateSyncedBusiness("showcaseTypeOther", event.target.value)} />
                </label>
              )}
              <label className="fullField">
                业务描述
                <textarea value={businessDraft.description} onChange={(event) => updateSyncedBusiness("description", event.target.value)} placeholder="服务对象、沟通方式和交付范围" />
              </label>
              <label>
                成稿内容 *
                <textarea value={businessDraft.finishedContent} onChange={(event) => updateSyncedBusiness("finishedContent", event.target.value)} placeholder="最终交付给客户的内容" />
              </label>
              <label>
                偏好类型
                <textarea value={businessDraft.preferredType} onChange={(event) => updateSyncedBusiness("preferredType", event.target.value)} placeholder="更愿意承接的题材或需求" />
              </label>
              <label className="fullField">
                不接类型 *
                <textarea value={businessDraft.excludedType} onChange={(event) => updateSyncedBusiness("excludedType", event.target.value)} placeholder="明确不承接的题材、用途或要求" />
              </label>
            </div>
            <div className="right">
              <Button light onClick={() => setPage("entry")}>取消</Button>
              <Button type="submit">确认并同步画像</Button>
            </div>
          </form>
        </Card>
      </>
    );
  if (page === "entry")
    return (
      <>
        <Head
          title="填写发布结果"
          sub="记录真实表现，用于下一轮复盘。"
          back={() => setPage("list")}
        />
        <Card>
          <div className="form resultBasics">
            <label>
              类型
              <select value={resultType} onChange={(event) => setResultType(event.target.value)}>
                <option>笔记</option>
                <option>业务</option>
              </select>
            </label>
            <label>
              发布时间
              <input type="datetime-local" value={publishedAt} onChange={(event) => setPublishedAt(event.target.value)} />
            </label>
          </div>
          <Note>复盘会结合发布时间与截至目前的累计数据，不直接比较不同观察时长的绝对数值。</Note>
          <div className="form resultMetrics">
            {(resultType === "业务"
              ? [["浏览", "浏览"], ["收藏", "收藏"], ["成交", "成交"]]
              : [["曝光", "截至目前的曝光量"], ["收藏", "收藏"], ["评论", "评论"]]
            ).map(([key, label]) => (
              <label key={key}>
                {label}
                <input
                  type="number"
                  min="0"
                  value={metrics[key] ?? 0}
                  onChange={(event) => setMetrics({ ...metrics, [key]: Number(event.target.value) })}
                />
              </label>
            ))}
          </div>
          <label>
            复盘备注
            <textarea
              value={metrics.备注}
              onChange={(e) => setMetrics({ ...metrics, 备注: e.target.value })}
              placeholder="记录用户反馈或本次执行变化"
            />
          </label>
          <div className="right">
            {resultType === "业务" && (
              <Button light onClick={openBusinessSync}>同步至画像</Button>
            )}
            <Button light onClick={() => toast("结果草稿已保存")}>
              保存草稿
            </Button>
            <Button onClick={submitOutcome}>提交本次结果</Button>
          </div>
        </Card>
      </>
    );
  if (page === "review")
    return (
      <>
        <Head
          title="结果复盘"
          sub="比较目标与真实结果，形成下一轮调整。"
          back={() => setPage("list")}
        />
        <Card>
          <Chip green>已复盘</Chip>
          <h2>{review?.summary || "等待 AI 根据本次回填结果生成复盘"}</h2>
          <p>
            {resultType === "业务"
              ? `浏览 ${Number(metrics.浏览 || 0).toLocaleString()}　收藏 ${Number(metrics.收藏 || 0)}　成交 ${Number(metrics.成交 || 0)}`
              : `截至目前的曝光量 ${Number(metrics.曝光 || 0).toLocaleString()}　收藏 ${Number(metrics.收藏 || 0)}　评论 ${Number(metrics.评论 || 0)}`}
          </p>
        </Card>
        <div className="grid3">
          <Card>
            <small>支持信号</small>
            <h3>{review?.positive_signals?.join("；") || "生成后展示"}</h3>
          </Card>
          <Card>
            <small>反向因素</small>
            <h3>{review?.counter_signals?.join("；") || "生成后展示"}</h3>
          </Card>
          <Card>
            <small>下一轮建议</small>
            <h3>{review?.next_actions?.join("；") || "生成后展示"}</h3>
          </Card>
        </div>
        <div className="right">
          <Button light onClick={generateReview} disabled={aiPending}>
            {aiPending ? "AI 复盘中…" : "生成 AI 复盘"}
          </Button>
          <Button light onClick={() => setModal(true)}>
            更新产能状态
          </Button>
          <Button onClick={() => go("console")}>开启下一轮</Button>
        </div>
        {modal && (
          <div className="overlay">
            <Card c="modal">
              <button
                className="close"
                onClick={() => setModal(false)}
                aria-label="关闭产能状态"
              >
                <X />
              </button>
              <h2>更新当前产能状态</h2>
              <div className="formats compact">
                {["可接单", "交付中", "满载", "暂停"].map((x) => (
                  <button
                    className={capacity === x ? "selected" : ""}
                    onClick={() => setCapacity(x)}
                    key={x}
                  >
                    {x}
                  </button>
                ))}
              </div>
              <Button
                onClick={() => {
                  setProfile({ ...profile, status: capacity });
                  toast("产能状态已同步更新");
                  setModal(false);
                }}
              >
                保存状态
              </Button>
            </Card>
          </div>
        )}
      </>
    );
  if (page === "detail")
    return (
      <>
        <Head
          title="历史方案详情"
          sub="查看当时确认的机会、策略和发布文字。"
          back={() => setPage("list")}
        />
        <Card>
          <Chip green>已完成</Chip>
          <h2>动物大头手绘挂件</h2>
          <p>小红书 · 图文 · 画像版本 V3 · 证据版本 E2</p>
          <h3>当时采用的策略</h3>
          <p>突出传统水彩、手作温度与定制沟通。</p>
          <div className="copy">
            标题：给毛孩子留下一份手绘纪念
            <br />
            <br />
            正文：从客户提供的照片开始……
          </div>
        </Card>
      </>
    );
  return (
    <>
      <Head
        title="历史与复盘"
        sub="查看已确认方案，并补充发布后的真实结果。"
        action={<Button onClick={() => setAddRecordOpen(true)}>添加记录</Button>}
      />
      <div className="grid3">
        {[
          ["已完成记录", "4"],
          ["待回填", "1"],
          ["已复盘", "2"],
        ].map((x) => (
          <Card key={x[0]}>
            <small>{x[0]}</small>
            <h2>{x[1]}</h2>
          </Card>
        ))}
      </div>
      <div className="filterBar">
        <label>
          时间
          <select value={timeFilter} onChange={(event) => setTimeFilter(event.target.value)}>
            <option>全部时间</option>
            <option>本周</option>
            <option>本月</option>
          </select>
        </label>
        <label>
          平台
          <select value={platformFilter} onChange={(event) => setPlatformFilter(event.target.value)}>
            <option>全部平台</option>
            <option>小红书</option>
            <option>画加</option>
          </select>
        </label>
        <label>
          状态
          <select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)}>
            <option>全部状态</option>
            <option>待回填</option>
            <option>已复盘</option>
          </select>
        </label>
        <label>
          类型
          <select value={typeFilter} onChange={(event) => setTypeFilter(event.target.value)}>
            <option>全部类型</option>
            <option>笔记</option>
            <option>业务</option>
          </select>
        </label>
      </div>
      {records.map((record) => (
        <Card c="record" key={record.id}>
          <div>
            <Chip green={record.status === "已复盘"}>{record.status}</Chip>
            <h3>{record.title}</h3>
            <p>
              {record.platform} · {record.type} · {record.period}
              {record.source ? ` · ${record.source}` : ""}
            </p>
          </div>
          <div className="buttonRow">
            <Button light onClick={() => setPage("detail")}>
              {record.source ? "查看记录" : "查看原方案"}
            </Button>
            <Button
              light
              onClick={() => {
                setActiveRecord(record);
                setResultType(record.type);
                if (record.publishedAt) setPublishedAt(record.publishedAt);
                if (record.source) {
                  setMetrics((current) => ({
                    ...current,
                    曝光: Number(record.exposure || 0),
                    浏览: Number(record.views || 0),
                    收藏: Number(record.favorites || 0),
                    评论: Number(record.comments || 0),
                    成交: Number(record.conversions || 0),
                    备注: record.note || "",
                  }));
                }
                setPage(record.status === "已复盘" ? "review" : "entry");
              }}
            >
              {record.status === "已复盘" ? "查看复盘" : "填写结果"}
            </Button>
          </div>
        </Card>
      ))}
      {!records.length && (
        <Card>
          <h3>没有符合当前筛选条件的记录</h3>
          <p>可以调整筛选条件，或添加一条自己发布的内容。</p>
        </Card>
      )}
      {addRecordOpen && (
        <div className="overlay">
          <Card c="modal addRecordModal">
            <button
              className="close"
              onClick={() => setAddRecordOpen(false)}
              aria-label="关闭添加记录"
            >
              <X />
            </button>
            <h2>添加发布记录</h2>
            <p className="modalIntro">
              记录未使用 AI 营销助手分析、由你自行发布的内容。
            </p>
            <form onSubmit={saveManualRecord}>
              <div className="form recordBasics">
                <label>
                  内容名称
                  <input
                    value={recordDraft.title}
                    onChange={(event) =>
                      setRecordDraft({ ...recordDraft, title: event.target.value })
                    }
                    placeholder="例如：宠物水彩挂件展示"
                  />
                </label>
                <label>
                  类型
                  <select
                    value={recordDraft.type}
                    onChange={(event) =>
                      setRecordDraft({ ...recordDraft, type: event.target.value })
                    }
                  >
                    <option>笔记</option>
                    <option>业务</option>
                  </select>
                </label>
                <label>
                  平台
                  <select
                    value={recordDraft.platform}
                    onChange={(event) =>
                      setRecordDraft({ ...recordDraft, platform: event.target.value })
                    }
                  >
                    <option>小红书</option>
                    <option>画加</option>
                  </select>
                </label>
                <label>
                  发布时间
                  <input
                    type="datetime-local"
                    value={recordDraft.publishedAt}
                    onChange={(event) =>
                      setRecordDraft({ ...recordDraft, publishedAt: event.target.value })
                    }
                  />
                </label>
              </div>
              <div className="form recordMetrics">
                {recordDraft.type === "笔记" ? (
                  <>
                    <label>
                      截至目前的曝光量
                      <input type="number" min="0" value={recordDraft.exposure} onChange={(event) => setRecordDraft({ ...recordDraft, exposure: event.target.value })} />
                    </label>
                    <label>
                      收藏
                      <input type="number" min="0" value={recordDraft.favorites} onChange={(event) => setRecordDraft({ ...recordDraft, favorites: event.target.value })} />
                    </label>
                    <label>
                      评论
                      <input type="number" min="0" value={recordDraft.comments} onChange={(event) => setRecordDraft({ ...recordDraft, comments: event.target.value })} />
                    </label>
                  </>
                ) : (
                  <>
                    <label>
                      浏览
                      <input type="number" min="0" value={recordDraft.views} onChange={(event) => setRecordDraft({ ...recordDraft, views: event.target.value })} />
                    </label>
                    <label>
                      收藏
                      <input type="number" min="0" value={recordDraft.favorites} onChange={(event) => setRecordDraft({ ...recordDraft, favorites: event.target.value })} />
                    </label>
                    <label>
                      成交
                      <input type="number" min="0" value={recordDraft.conversions} onChange={(event) => setRecordDraft({ ...recordDraft, conversions: event.target.value })} />
                    </label>
                  </>
                )}
              </div>
              <label>
                备注（选填）
                <textarea
                  value={recordDraft.note}
                  onChange={(event) =>
                    setRecordDraft({ ...recordDraft, note: event.target.value })
                  }
                  placeholder="记录发布背景、执行变化或其他需要复盘的信息"
                />
              </label>
              <div className="right">
                <Button light onClick={() => setAddRecordOpen(false)}>取消</Button>
                <Button type="submit">保存记录</Button>
              </div>
            </form>
          </Card>
        </div>
      )}
    </>
  );
}

function ContextRail() {
  return (
    <aside className="rail">
      <h3>本轮任务进度</h3>
      <p className="railIntro">
        围绕同一个营销目标推进，详细分析仍在各专业页面完成。
      </p>
      <div className="timeline">
        {[
          ["done", "画像已确认", "能力、价格与产能可用"],
          ["done", "市场信息可用", "小红书与画加已更新"],
          ["current", "选择机会方向", "当前需要处理"],
          ["pending", "完善营销方案", "方向确认后开始"],
          ["pending", "发布并回填结果", "形成下一轮复盘"],
        ].map(([state, title, sub]) => (
          <div className={"timelineItem " + state} key={title}>
            <i />
            <div>
              <b>{title}</b>
              <small>{sub}</small>
            </div>
            {state === "current" && <Chip>当前</Chip>}
          </div>
        ))}
      </div>
    </aside>
  );
}
function Product({ goLanding, session }) {
  const [v, setV] = useStored("ama-view", "console"),
    [profile, setProfile] = useStored("ama-profile", EMPTY_PROFILE),
    [profileEstablished, setProfileEstablished] = useStored(
      "ama-profile-established",
      false,
    ),
    [legacyChatMessages] = useStored("ama-chat-messages-v2", []),
    [chatThreads, setChatThreads] = useStored("ama-chat-threads", []),
    [activeChatId, setActiveChatId] = useStored("ama-active-chat", ""),
    [message, setMessage] = useState(""),
    workRef = useRef(null);
  useEffect(() => {
    if (workRef.current) workRef.current.scrollTop = 0;
  }, [v]);
  useEffect(() => {
    if (!chatThreads.length && legacyChatMessages.length) {
      const migrated = {
        id: "chat-migrated",
        title:
          legacyChatMessages.find((item) => item.role === "user")?.text?.slice(0, 18) ||
          "营销助理对话",
        messages: legacyChatMessages,
        updatedAt: new Date().toISOString(),
      };
      setChatThreads([migrated]);
      setActiveChatId(migrated.id);
    }
  }, [chatThreads.length, legacyChatMessages, setActiveChatId, setChatThreads]);
  useEffect(() => {
    getAPI("/workflow/context/" + currentUserId())
      .then((data) => {
        const confirmed = data.memory?.confirmed_profile;
        if (!confirmed) return;
        setProfileEstablished(true);
        const goals = confirmed.business_goals || {};
        const capabilities = confirmed.creator_capabilities || {};
        const userReported = confirmed.platform_facts?.user_reported || {};
        const statusPreference = data.memory?.confirmed_preferences?.find(
          (item) => item.key === "capacity_status",
        );
        const statusMap = {
          available: "可接单",
          near_limit: "交付中",
          full: "满载",
        };
        setProfile((current) => ({
          ...current,
          goal: goals.primary_goal || current.goal,
          direction: goals.target_direction || current.direction,
          customers: (goals.target_customers || []).join("、") || current.customers,
          topics: (capabilities.subjects || []).join("、") || current.topics,
          styles: (capabilities.styles || []).join("、") || current.styles,
          services: (capabilities.services || []).join("、") || current.services,
          boundaries:
            (goals.excluded_business || []).join("；") || current.boundaries,
          status: statusMap[statusPreference?.value] || current.status,
          existingBusinesses: capabilities.existing_businesses?.length
            ? capabilities.existing_businesses.map((business, index) => ({
                ...createBusinessDraft(),
                ...business,
                id: business.id || `business-saved-${index + 1}`,
              }))
            : current.existingBusinesses,
          manualPlatformData: Object.keys(userReported).length
            ? userReported
            : current.manualPlatformData,
        }));
      })
      .catch(() => {});
  }, [setProfile, setProfileEstablished]);
  const toast = (x) => {
    setMessage(x);
    setTimeout(() => setMessage(""), 2200);
  };
  const chatMessages =
    chatThreads.find((thread) => thread.id === activeChatId)?.messages || [];
  const setChatMessages = useCallback(
    (next) => {
      setChatThreads((current) =>
        current.map((thread) => {
          if (thread.id !== activeChatId) return thread;
          const messages =
            typeof next === "function" ? next(thread.messages) : next;
          const firstQuestion = messages.find((item) => item.role === "user")?.text;
          return {
            ...thread,
            title:
              thread.title === "新对话" && firstQuestion
                ? firstQuestion.slice(0, 18)
                : thread.title,
            messages,
            updatedAt: new Date().toISOString(),
          };
        }),
      );
    },
    [activeChatId, setChatThreads],
  );
  const openChat = (text) => {
    const id = `chat-${Date.now()}`;
    setChatThreads((current) => [
      {
        id,
        title: text.slice(0, 18),
        messages: [{ role: "user", text }],
        updatedAt: new Date().toISOString(),
      },
      ...current,
    ]);
    setActiveChatId(id);
    setV("chat");
  };
  const openThread = (id) => {
    setActiveChatId(id);
    setV("chat");
  };
  const newThread = () => {
    const id = `chat-${Date.now()}`;
    setChatThreads((current) => [
      { id, title: "新对话", messages: [], updatedAt: new Date().toISOString() },
      ...current,
    ]);
    setActiveChatId(id);
    setV("chat");
  };
  const C =
    {
      console: Console,
      profile: Profile,
      market: Market,
      decision: DecisionScored,
      plan: Plan,
      history: History,
      chat: Chat,
    }[v] || Console;
  return (
    <div className="app">
      <Sidebar
        view={v}
        setView={setV}
        goLanding={goLanding}
        chatThreads={chatThreads}
        activeChatId={activeChatId}
        openThread={openThread}
        newThread={newThread}
        displayName={session?.user?.display_name}
        onLogout={() => {
          postAPI("/auth/logout", {}).catch(() => {});
          localStorage.removeItem(AUTH_KEY);
          window.location.assign("/");
        }}
      />
      <main className="work" ref={workRef}>
        <div className={"route-" + v}>
          <C
            go={setV}
            profile={profile}
            setProfile={setProfile}
            profileEstablished={profileEstablished}
            setProfileEstablished={setProfileEstablished}
            toast={toast}
            openChat={openChat}
            messages={chatMessages}
            setMessages={setChatMessages}
          />
        </div>
      </main>
      {v === "console" && <ContextRail />}
      {message && (
        <div className="toast" role="status" aria-live="polite">
          <Check size={16} />
          {message}
        </div>
      )}
    </div>
  );
}
export default function App() {
  const [r, setR] = useStored("ama-route", "landing");
  const [session, setSession] = useState(readSession());
  const handleLogin = async (nextSession) => {
    setSession(nextSession);
    try {
      const context = await getAPI(
        "/workflow/context/" + nextSession.user.user_id,
      );
      setR(context.memory?.confirmed_profile ? "product" : "setup");
    } catch {
      setR("setup");
    }
  };
  if (!session && !["landing", "login"].includes(r)) {
    return <Login go={setR} onLogin={handleLogin} />;
  }
  return r === "landing" ? (
    <Landing go={setR} />
  ) : r === "login" ? (
    <Login go={setR} onLogin={handleLogin} />
  ) : r === "setup" ? (
    <Setup go={setR} />
  ) : (
    <Product goLanding={() => setR("landing")} session={session} />
  );
}
