import {
  AlertTriangle,
  BarChart3,
  CalendarDays,
  CheckCircle2,
  Clock3,
  CreditCard,
  Edit3,
  FileText,
  Globe2,
  LogOut,
  Menu,
  PauseCircle,
  Plus,
  RefreshCcw,
  Settings,
  ShieldCheck,
  Trash2,
  XCircle
} from "lucide-react";
import { useMemo, useState, useEffect } from "react";

type View = "calendar" | "posts" | "analytics" | "settings";
type PostStatus = "scheduled" | "posted" | "failed" | "canceled";
type UserStatus = "active" | "paused" | "suspended";
type PostSort = "newest" | "oldest" | "status";

type ScheduledPost = {
  id: string;
  content: string;
  date: string;
  time: string;
  timezone: string;
  status: PostStatus;
  failureReason?: string;
  metrics?: {
    views: number;
    likes: number;
    replies: number;
    reposts: number;
    quotes: number;
    shares: number;
  };
};

const localeLabels = [
  { code: "ja", label: "日本語" },
  { code: "en", label: "English" },
  { code: "zh", label: "中文" },
  { code: "fil", label: "Filipino" },
  { code: "vi", label: "Tiếng Việt" }
];

const initialPosts: ScheduledPost[] = [
  {
    id: "post-001",
    content: "Schedule For SNSの初期画面を整えています。予約投稿をもっと軽く。",
    date: "2026-05-02",
    time: "09:30",
    timezone: "Asia/Tokyo",
    status: "scheduled"
  },
  {
    id: "post-002",
    content: "投稿から24時間の基本分析を確認。累計値だけに絞ると運用が楽です。",
    date: "2026-05-01",
    time: "13:00",
    timezone: "Asia/Tokyo",
    status: "posted",
    metrics: {
      views: 1280,
      likes: 96,
      replies: 11,
      reposts: 7,
      quotes: 3,
      shares: 14
    }
  },
  {
    id: "post-003",
    content: "再連携チェックの挙動確認用投稿です。",
    date: "2026-05-01",
    time: "16:00",
    timezone: "Asia/Tokyo",
    status: "failed",
    failureReason: "Threads再連携が必要"
  }
];

const statusMeta: Record<PostStatus, { label: string; icon: typeof Clock3; tone: string }> = {
  scheduled: { label: "予約済み", icon: Clock3, tone: "info" },
  posted: { label: "投稿済み", icon: CheckCircle2, tone: "success" },
  failed: { label: "失敗", icon: XCircle, tone: "danger" },
  canceled: { label: "キャンセル済み", icon: PauseCircle, tone: "muted" }
};

function App() {
  const apiBaseUrl = import.meta.env.VITE_API_BASE_URL;

  const handleThreadsLogin = () => {
    const returnTo = window.location.origin;
  
    window.location.href =
      `${apiBaseUrl}/auth/threads/start?return_to=${encodeURIComponent(returnTo)}`;
  };

  const handleLogout = () => {
    fetch(`${apiBaseUrl}/auth/logout`, {
      method: "POST",
      credentials: "include",
    }).then(() => {
      window.location.reload();
    });
  };

  const [view, setView] = useState<View>("calendar");
  const [menuOpen, setMenuOpen] = useState(false);
  const [userStatus, setUserStatus] = useState<UserStatus>("active");
  const [needsReconnect, setNeedsReconnect] = useState(true);
  const [selectedDate, setSelectedDate] = useState("2026-05-02");
  const [visibleMonth, setVisibleMonth] = useState("2026-05");
  const [posts, setPosts] = useState(initialPosts);
  const [draft, setDraft] = useState({
    date: "2026-05-02",
    time: "10:00",
    timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || "Asia/Tokyo",
    content: ""
  });
  const [editingId, setEditingId] = useState<string | null>(null);
  const [showConfirm, setShowConfirm] = useState(false);

  const selectedPosts = posts.filter((post) => post.date === selectedDate && post.status === "scheduled");
  const remainingSlots = Math.max(0, 3 - selectedPosts.length);
  const activePosts = posts.filter((post) => post.status === "scheduled");
  const postedPosts = posts.filter((post) => post.status === "posted");

  const analytics = useMemo(() => {
    return postedPosts.reduce(
      (total, post) => {
        const metrics = post.metrics;
        if (!metrics) return total;
        total.views += metrics.views;
        total.likes += metrics.likes;
        total.replies += metrics.replies;
        total.reposts += metrics.reposts;
        total.quotes += metrics.quotes;
        total.shares += metrics.shares;
        return total;
      },
      { views: 0, likes: 0, replies: 0, reposts: 0, quotes: 0, shares: 0 }
    );
  }, [postedPosts]);

  const engagement = analytics.likes + analytics.replies + analytics.reposts + analytics.quotes + analytics.shares;
  const isBlocked = userStatus !== "active" || needsReconnect;
  
  const [isLoggedIn, setIsLoggedIn] = useState<boolean | null>(null);

  useEffect(() => {
    fetch(`${apiBaseUrl}/me`, {
      credentials: "include"
    })
      .then((res) => {
        setIsLoggedIn(res.ok);
      })
      .catch(() => {
        setIsLoggedIn(false);
      });
  }, [apiBaseUrl]);

  function resetDraft() {
    setDraft({
      date: selectedDate,
      time: "10:00",
      timezone: draft.timezone,
      content: ""
    });
    setEditingId(null);
    setShowConfirm(false);
  }

  function beginEdit(post: ScheduledPost) {
    setEditingId(post.id);
    setDraft({
      date: post.date,
      time: post.time,
      timezone: post.timezone,
      content: post.content
    });
    setView("calendar");
  }

  function saveDraft() {
    if (!draft.content.trim()) return;

    if (editingId) {
      setPosts((current) =>
        current.map((post) =>
          post.id === editingId
            ? {
                ...post,
                content: draft.content.trim(),
                date: draft.date,
                time: draft.time,
                timezone: draft.timezone
              }
            : post
        )
      );
    } else {
      setPosts((current) => [
        {
          id: `post-${current.length + 1}`.padStart(8, "0"),
          content: draft.content.trim(),
          date: draft.date,
          time: draft.time,
          timezone: draft.timezone,
          status: "scheduled"
        },
        ...current
      ]);
    }

    setSelectedDate(draft.date);
    resetDraft();
  }

  function deletePost(id: string) {
    setPosts((current) =>
      current.map((post) => (post.id === id && post.status === "scheduled" ? { ...post, status: "canceled" } : post))
    );
  }

  function cloneFailed(post: ScheduledPost) {
    setEditingId(null);
    setDraft({
      date: selectedDate,
      time: "10:00",
      timezone: post.timezone,
      content: post.content
    });
    setView("calendar");
  }

  if (isLoggedIn === null) {
    return <div>Loading...</div>;
  }

  if (!isLoggedIn) {
    return (
      <div className="login-page">
        <div className="login-card">
          <h1>Schedule For SNS</h1>
          <p>Threadsの投稿を、カレンダーからかんたんに予約できます。</p>
  
          <button className="button primary" onClick={handleThreadsLogin}>
            Threadsでログイン
          </button>
  
          <p className="muted-text">14日間無料。その後は税込390円/月。</p>
        </div>
      </div>
    );
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand-lockup">
          <div className="brand-mark">S4S</div>
          <div>
            <strong>Schedule For SNS</strong>
            <span>Threads scheduler</span>
          </div>
        </div>

        <div className="mobile-header-actions">
          <div className="mobile-trial-chip">
            <Clock3 size={15} />
            <span>Trial 13日 04:22</span>
          </div>
          <button
            aria-expanded={menuOpen}
            aria-label="メニューを開閉"
            className="hamburger-button"
            onClick={() => setMenuOpen((open) => !open)}
          >
            <Menu size={22} />
          </button>
        </div>

        <nav className={`nav-stack ${menuOpen ? "open" : ""}`} aria-label="メイン">
          <NavButton active={view === "calendar"} icon={CalendarDays} label="予約作成" onClick={() => { setView("calendar"); setMenuOpen(false); }} />
          <NavButton active={view === "posts"} icon={FileText} label="予約一覧" onClick={() => { setView("posts"); setMenuOpen(false); }} />
          <NavButton active={view === "analytics"} icon={BarChart3} label="分析" onClick={() => { setView("analytics"); setMenuOpen(false); }} />
          <NavButton active={view === "settings"} icon={Settings} label="設定" onClick={() => { setView("settings"); setMenuOpen(false); }} />
        </nav>

        <div className="trial-panel">
          <span>無料トライアル</span>
          <strong>13日 04:22</strong>
          <small>終了後 税込390円/月</small>
        </div>
      </aside>

      <main className="main-surface">
        <header className="topbar">
          <div>
            <p className="eyebrow">2026年5月1日 金曜日</p>
            <h1>{viewTitle(view)}</h1>
          </div>
          <div className="topbar-actions">
            <select aria-label="表示言語" defaultValue="ja">
              {localeLabels.map((locale) => (
                <option key={locale.code} value={locale.code}>
                  {locale.label}
                </option>
              ))}
            </select>
          <button
            className="icon-button"
            title="ログアウト"
            onClick={handleLogout}
          >
            <LogOut size={18} />
          </button>
          </div>
        </header>

        <section className="notice-band">
          <ShieldCheck size={18} />
          <span>Meta App Review向けに、投稿予約と基本分析に必要な最小スコープだけを使います。</span>
        </section>

        {needsReconnect && (
          <section className="dialog-banner danger">
            <AlertTriangle size={20} />
            <div>
              <strong>Threads再連携が必要です</strong>
              <span>再連携が完了するまで予約作成と投稿実行は停止されます。</span>
            </div>
            <button className="button dark" onClick={() => setNeedsReconnect(false)}>
              <RefreshCcw size={16} />
              再連携する
            </button>
          </section>
        )}

        {userStatus === "paused" && (
          <section className="dialog-banner">
            <PauseCircle size={20} />
            <div>
              <strong>休止中です</strong>
              <span>利用には再開が必要です。再開するまで予約・分析は停止されます。</span>
            </div>
            <button className="button dark" onClick={() => setUserStatus("active")}>
              再開する
            </button>
          </section>
        )}

        {view === "calendar" && (
          <CalendarView
            activePosts={activePosts}
            draft={draft}
            editingId={editingId}
            isBlocked={isBlocked}
            remainingSlots={remainingSlots}
            selectedDate={selectedDate}
            selectedPosts={selectedPosts}
            setDraft={setDraft}
            setSelectedDate={setSelectedDate}
            setShowConfirm={setShowConfirm}
            setVisibleMonth={setVisibleMonth}
            visibleMonth={visibleMonth}
          />
        )}

        {view === "posts" && (
          <PostsView posts={posts} onCloneFailed={cloneFailed} onDelete={deletePost} onEdit={beginEdit} />
        )}

        {view === "analytics" && <AnalyticsView analytics={analytics} engagement={engagement} postedPosts={postedPosts} />}

        {view === "settings" && (
          <SettingsView
            needsReconnect={needsReconnect}
            setNeedsReconnect={setNeedsReconnect}
            setUserStatus={setUserStatus}
            userStatus={userStatus}
          />
        )}
      </main>

      {showConfirm && (
        <ConfirmDialog
          draft={draft}
          editingId={editingId}
          onCancel={() => setShowConfirm(false)}
          onConfirm={saveDraft}
        />
      )}
    </div>
  );
}

function viewTitle(view: View) {
  const titles: Record<View, string> = {
    calendar: "予約作成",
    posts: "予約一覧",
    analytics: "投稿分析",
    settings: "設定"
  };
  return titles[view];
}

function NavButton({
  active,
  icon: Icon,
  label,
  onClick
}: {
  active: boolean;
  icon: typeof CalendarDays;
  label: string;
  onClick: () => void;
}) {
  return (
    <button className={`nav-button ${active ? "active" : ""}`} onClick={onClick}>
      <Icon size={18} />
      <span>{label}</span>
    </button>
  );
}

function CalendarView({
  activePosts,
  draft,
  editingId,
  isBlocked,
  remainingSlots,
  selectedDate,
  selectedPosts,
  setDraft,
  setSelectedDate,
  setShowConfirm,
  setVisibleMonth,
  visibleMonth
}: {
  activePosts: ScheduledPost[];
  draft: { date: string; time: string; timezone: string; content: string };
  editingId: string | null;
  isBlocked: boolean;
  remainingSlots: number;
  selectedDate: string;
  selectedPosts: ScheduledPost[];
  setDraft: (draft: { date: string; time: string; timezone: string; content: string }) => void;
  setSelectedDate: (date: string) => void;
  setShowConfirm: (show: boolean) => void;
  setVisibleMonth: (month: string) => void;
  visibleMonth: string;
}) {
  const dates = useMemo(() => buildMonthDates(visibleMonth), [visibleMonth]);
  const [year, month] = visibleMonth.split("-");
  const isFull = remainingSlots === 0 && !editingId;
  const canSubmit = !isBlocked && !isFull && draft.content.trim().length > 0;

  return (
    <div className="workspace-grid">
      <section className="panel calendar-panel">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Calendar</p>
            <h2>日付を選択</h2>
          </div>
          <span className="pill">{remainingSlots}/3 枠</span>
        </div>
        <div className="month-controls">
          <label>
            年
            <select value={year} onChange={(event) => setVisibleMonth(`${event.target.value}-${month}`)}>
              {[2026, 2027, 2028].map((value) => (
                <option key={value} value={value}>
                  {value}
                </option>
              ))}
            </select>
          </label>
          <label>
            月
            <select value={month} onChange={(event) => setVisibleMonth(`${year}-${event.target.value}`)}>
              {Array.from({ length: 12 }, (_, index) => `${index + 1}`.padStart(2, "0")).map((value) => (
                <option key={value} value={value}>
                  {Number(value)}月
                </option>
              ))}
            </select>
          </label>
        </div>
        <div className="date-grid">
          {dates.map((date) => {
            const count = activePosts.filter((post) => post.date === date).length;
            return (
              <button
                className={`date-cell ${selectedDate === date ? "selected" : ""}`}
                key={date}
                onClick={() => {
                  setSelectedDate(date);
                  setDraft({ ...draft, date });
                }}
              >
                <strong>{date.slice(8)}</strong>
                <span>{weekdayLabel(date)}</span>
                <small>{count} 件</small>
              </button>
            );
          })}
        </div>
        <div className="day-list">
          <h3>選択日の予約</h3>
          {selectedPosts.length === 0 ? (
            <p className="muted-text">この日の予約はまだありません。</p>
          ) : (
            selectedPosts.map((post) => (
              <div className="compact-row" key={post.id}>
                <Clock3 size={16} />
                <span>{post.time}</span>
                <strong>{post.content}</strong>
              </div>
            ))
          )}
        </div>
      </section>

      <section className="panel composer-panel">
        <div className="section-heading">
          <div>
            <p className="eyebrow">{editingId ? "Edit" : "New post"}</p>
            <h2>{editingId ? "予約を編集" : "投稿を予約"}</h2>
          </div>
          <span className="pill muted">5分以内不可</span>
        </div>
        <div className="form-grid">
          <label>
            日付
            <input type="date" value={draft.date} onChange={(event) => setDraft({ ...draft, date: event.target.value })} />
          </label>
          <label>
            時刻
            <input type="time" value={draft.time} onChange={(event) => setDraft({ ...draft, time: event.target.value })} />
          </label>
          <label className="wide">
            タイムゾーン
            <select value={draft.timezone} onChange={(event) => setDraft({ ...draft, timezone: event.target.value })}>
              <option value="Asia/Tokyo">Asia/Tokyo</option>
              <option value="America/Los_Angeles">America/Los_Angeles</option>
              <option value="Europe/London">Europe/London</option>
              <option value="Asia/Manila">Asia/Manila</option>
              <option value="Asia/Ho_Chi_Minh">Asia/Ho_Chi_Minh</option>
            </select>
          </label>
          <label className="wide">
            投稿本文
            <textarea
              maxLength={500}
              placeholder="Threadsへ投稿する本文を入力"
              value={draft.content}
              onChange={(event) => setDraft({ ...draft, content: event.target.value })}
            />
          </label>
        </div>
        <div className="composer-footer">
          <span>{draft.content.length}/500</span>
          <button className="button primary" disabled={!canSubmit} onClick={() => setShowConfirm(true)}>
            {editingId ? <Edit3 size={16} /> : <Plus size={16} />}
            {editingId ? "編集内容を確認" : "予約内容を確認"}
          </button>
        </div>
      </section>
    </div>
  );
}

function PostsView({
  posts,
  onCloneFailed,
  onDelete,
  onEdit
}: {
  posts: ScheduledPost[];
  onCloneFailed: (post: ScheduledPost) => void;
  onDelete: (id: string) => void;
  onEdit: (post: ScheduledPost) => void;
}) {
  const [sort, setSort] = useState<PostSort>("newest");
  const sortedPosts = useMemo(() => sortPosts(posts, sort), [posts, sort]);

  return (
    <section className="panel">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Posts</p>
          <h2>予約と投稿履歴</h2>
        </div>
        <label className="sort-control">
          並び替え
          <select value={sort} onChange={(event) => setSort(event.target.value as PostSort)}>
            <option value="newest">新しい順</option>
            <option value="oldest">古い順</option>
            <option value="status">ステータス順</option>
          </select>
        </label>
      </div>
      <div className="post-list">
        {sortedPosts.map((post) => {
          const meta = statusMeta[post.status];
          const Icon = meta.icon;
          return (
            <article className="post-row" key={post.id}>
              <div className={`status-dot ${meta.tone}`}>
                <Icon size={17} />
              </div>
              <div className="post-main">
                <div className="post-meta">
                  <span>{post.date}</span>
                  <span>{post.time}</span>
                  <span>{post.timezone}</span>
                  <strong>{meta.label}</strong>
                </div>
                <p>{post.content}</p>
                {post.failureReason && <small className="failure-text">{post.failureReason}</small>}
              </div>
              <div className="row-actions">
                {post.status === "scheduled" && (
                  <>
                    <button className="icon-button" title="編集" onClick={() => onEdit(post)}>
                      <Edit3 size={17} />
                    </button>
                    <button className="icon-button" title="削除" onClick={() => onDelete(post.id)}>
                      <Trash2 size={17} />
                    </button>
                  </>
                )}
                {post.status === "failed" && (
                  <button className="button secondary" onClick={() => onCloneFailed(post)}>
                    <RefreshCcw size={16} />
                    同じ本文で予約
                  </button>
                )}
              </div>
            </article>
          );
        })}
      </div>
    </section>
  );
}

function buildMonthDates(month: string) {
  const [year, monthIndex] = month.split("-").map(Number);
  const lastDay = new Date(year, monthIndex, 0).getDate();
  return Array.from({ length: lastDay }, (_, index) => {
    const day = `${index + 1}`.padStart(2, "0");
    return `${year}-${`${monthIndex}`.padStart(2, "0")}-${day}`;
  });
}

function weekdayLabel(date: string) {
  const formatter = new Intl.DateTimeFormat("ja-JP", { weekday: "short" });
  return formatter.format(new Date(`${date}T00:00:00+09:00`));
}

function sortPosts(posts: ScheduledPost[], sort: PostSort) {
  const sorted = [...posts];
  if (sort === "status") {
    const order: Record<PostStatus, number> = {
      failed: 0,
      scheduled: 1,
      posted: 2,
      canceled: 3
    };
    return sorted.sort((a, b) => order[a.status] - order[b.status] || postTimestamp(b).localeCompare(postTimestamp(a)));
  }
  return sorted.sort((a, b) =>
    sort === "newest"
      ? postTimestamp(b).localeCompare(postTimestamp(a))
      : postTimestamp(a).localeCompare(postTimestamp(b))
  );
}

function postTimestamp(post: ScheduledPost) {
  return `${post.date}T${post.time}`;
}

function AnalyticsView({
  analytics,
  engagement,
  postedPosts
}: {
  analytics: { views: number; likes: number; replies: number; reposts: number; quotes: number; shares: number };
  engagement: number;
  postedPosts: ScheduledPost[];
}) {
  const statItems = [
    { label: "閲覧", value: analytics.views },
    { label: "いいね", value: analytics.likes },
    { label: "返信", value: analytics.replies },
    { label: "リポスト", value: analytics.reposts },
    { label: "引用", value: analytics.quotes },
    { label: "シェア", value: analytics.shares }
  ];

  return (
    <div className="analytics-layout">
      <section className="metric-strip">
        {statItems.map((item) => (
          <div className="metric" key={item.label}>
            <span>{item.label}</span>
            <strong>{item.value.toLocaleString()}</strong>
          </div>
        ))}
        <div className="metric strong">
          <span>合計エンゲージメント</span>
          <strong>{engagement.toLocaleString()}</strong>
        </div>
      </section>
      <section className="panel">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Ranking</p>
            <h2>反応が良かった投稿</h2>
          </div>
          <span className="pill muted">累計値</span>
        </div>
        <div className="post-list">
          {postedPosts.map((post) => (
            <article className="post-row" key={post.id}>
              <div className="status-dot success">
                <BarChart3 size={17} />
              </div>
              <div className="post-main">
                <div className="post-meta">
                  <span>{post.date}</span>
                  <span>1h / 24h / 72h</span>
                </div>
                <p>{post.content}</p>
              </div>
              <strong>{post.metrics ? post.metrics.likes + post.metrics.replies + post.metrics.reposts + post.metrics.quotes + post.metrics.shares : 0}</strong>
            </article>
          ))}
        </div>
      </section>
    </div>
  );
}

function SettingsView({
  needsReconnect,
  setNeedsReconnect,
  setUserStatus,
  userStatus
}: {
  needsReconnect: boolean;
  setNeedsReconnect: (needsReconnect: boolean) => void;
  setUserStatus: (status: UserStatus) => void;
  userStatus: UserStatus;
}) {
  return (
    <div className="settings-layout">
      <section className="panel">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Account</p>
            <h2>連携と状態</h2>
          </div>
        </div>
        <div className="settings-list">
          <SettingRow icon={Globe2} label="表示言語" value="日本語" />
          <SettingRow icon={Clock3} label="タイムゾーン" value="Asia/Tokyo" />
          <SettingRow icon={RefreshCcw} label="Threads連携" value={needsReconnect ? "再連携が必要" : "有効"} />
          <SettingRow icon={PauseCircle} label="利用状態" value={userStatus === "paused" ? "休止中" : "有効"} />
          <SettingRow icon={CreditCard} label="次回請求" value="2026-05-15 / 税込390円" />
        </div>
        <div className="button-row">
          <button className="button secondary" onClick={() => setNeedsReconnect(false)}>
            <RefreshCcw size={16} />
            Threads再連携
          </button>
          <button className="button secondary" onClick={() => setUserStatus(userStatus === "paused" ? "active" : "paused")}>
            <PauseCircle size={16} />
            {userStatus === "paused" ? "再開する" : "休止にする"}
          </button>
          <button className="button danger">
            <Trash2 size={16} />
            退会
          </button>
        </div>
      </section>
      <section className="panel">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Legal</p>
            <h2>法務文書</h2>
          </div>
        </div>
        <div className="legal-links">
          <a href="/docs/legal-policies.md">特定商取引法に基づく表記</a>
          <a href="/docs/legal-policies.md">利用規約</a>
          <a href="/docs/legal-policies.md">プライバシーポリシー</a>
        </div>
      </section>
    </div>
  );
}

function SettingRow({ icon: Icon, label, value }: { icon: typeof Globe2; label: string; value: string }) {
  return (
    <div className="setting-row">
      <Icon size={18} />
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function ConfirmDialog({
  draft,
  editingId,
  onCancel,
  onConfirm
}: {
  draft: { date: string; time: string; timezone: string; content: string };
  editingId: string | null;
  onCancel: () => void;
  onConfirm: () => void;
}) {
  return (
    <div className="modal-backdrop" role="presentation">
      <section className="modal-panel" role="dialog" aria-modal="true" aria-labelledby="confirm-title">
        <h2 id="confirm-title">{editingId ? "編集内容を確認" : "予約内容を確認"}</h2>
        <dl className="confirm-list">
          <div>
            <dt>日時</dt>
            <dd>
              {draft.date} {draft.time}
            </dd>
          </div>
          <div>
            <dt>タイムゾーン</dt>
            <dd>{draft.timezone}</dd>
          </div>
          <div>
            <dt>本文</dt>
            <dd>{draft.content}</dd>
          </div>
        </dl>
        <div className="button-row end">
          <button className="button secondary" onClick={onCancel}>
            戻る
          </button>
          <button className="button primary" onClick={onConfirm}>
            {editingId ? "更新する" : "予約する"}
          </button>
        </div>
      </section>
    </div>
  );
}

export default App;
