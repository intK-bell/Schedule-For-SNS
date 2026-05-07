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
  RefreshCcw,
  Settings,
  ShieldCheck,
  Trash2,
  Wrench,
  XCircle
} from "lucide-react";
import { type ReactNode, useCallback, useEffect, useMemo, useRef, useState } from "react";
import legalPoliciesText from "../docs/legal-policies.md?raw";

type View = "calendar" | "posts" | "analytics" | "settings" | "developer";
type LegalDocument = "commerce" | "terms" | "privacy";
type LocaleCode = "ja" | "en" | "zh" | "fil" | "vi";
type PostStatus = "scheduled" | "posted" | "failed" | "canceled";
type UserStatus = "active" | "paused" | "suspended";
type SubscriptionStatus = "trialing" | "active" | "trial_expired" | "past_due" | "canceled" | "unpaid" | "incomplete" | "cancel_pending_admin_review";
type PostSort = "newest" | "oldest" | "status";

type ScheduledPost = {
  id: string;
  content: string;
  date: string;
  time: string;
  timezone: string;
  status: PostStatus;
  failureReason?: string;
  analyticsStage?: string;
  analyticsFetchedAt?: number;
  metrics?: {
    views: number;
    likes: number;
    replies: number;
    reposts: number;
    quotes: number;
    shares: number;
  };
};

type ApiScheduledPost = {
  post_id: string;
  content: string;
  scheduled_at: string;
  timezone?: string;
  status?: string;
  failure_reason?: string;
  analytics_stage?: string;
  analytics_fetched_at?: number;
  metrics?: ScheduledPost["metrics"];
};

type DeveloperDashboard = {
  metrics: {
    total_users: number;
    trial_users: number;
    subscribed_users: number;
    conversion_base_users: number;
    cvr: number;
    admin_review_items: number;
    subscriptions_total: number;
    subscriptions_requiring_review: number;
  };
  admin_review_items: Array<{
    app_user_id: string;
    threads_user_id: string;
    display_name: string;
    status: string;
    reason: string;
    stripe_subscription_id: string;
    stripe_cancel_failed_at: number;
    stripe_cancel_error: string;
    updated_at: number;
  }>;
};

const localeLabels: Array<{ code: LocaleCode; flag: string; label: string }> = [
  { code: "ja", flag: "🇯🇵", label: "日本語" },
  { code: "en", flag: "🇺🇸", label: "English" },
  { code: "zh", flag: "🇨🇳", label: "中文" },
  { code: "fil", flag: "🇵🇭", label: "Filipino" },
  { code: "vi", flag: "🇻🇳", label: "Tiếng Việt" }
];

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const uiText: Record<LocaleCode, any> = {
  ja: {
    loading: "Loading...",
    loginEyebrow: "Threads scheduler",
    loginLead: "Threadsの投稿を、カレンダーからかんたんに予約できます。",
    loginButton: "Threadsでログイン",
    trialOffer: "14日間無料。その後は税込390円/月。",
    loginLanguage: "表示言語",
    loginHighlights: ["30日先まで予約", "1日3件まで投稿予約", "基本分析を確認"],
    serviceSubtitle: "Threads scheduler",
    menuToggle: "メニューを開閉",
    mainNav: "メイン",
    logout: "ログアウト",
    nav: { calendar: "予約作成", posts: "予約一覧", analytics: "分析", settings: "設定", developer: "開発者" },
    billing: {
      active: "登録済み",
      activeBadge: "サブスク有効",
      required: "登録が必要",
      trial: "無料トライアル",
      trialing: "トライアル中",
      trialExpired: "トライアル終了",
      remaining: (days: number, hours: number) => `残り${days}日 ${hours}時間`,
      period: (start: string, end: string) => `開始 ${start} / 終了 ${end}`,
      unset: "未設定",
      checkout: "今すぐ登録",
      portal: "支払い方法を変更",
      expiredTitle: "無料トライアルが終了しました",
      expiredBody: (period: string) => `${period}。予約作成、編集、投稿実行、分析取得には月額390円の登録が必要です。`,
    },
    notice: "Meta App Review向けに、投稿予約と基本分析に必要な最小スコープだけを使います。",
    reconnect: {
      title: "Threads再連携が必要です",
      body: "再連携が完了するまで予約作成と投稿実行は停止されます。",
      button: "再連携する",
      shortButton: "再連携",
      needed: "再連携が必要",
      enabled: "有効",
    },
    paused: {
      title: "休止中です",
      body: "利用には再開が必要です。再開するまで予約・分析は停止されます。",
      resume: "再開する",
      pause: "休止にする",
      active: "有効",
      paused: "休止中",
    },
    calendar: {
      eyebrow: "Calendar",
      title: "日付を選択",
      slots: (remaining: number) => `${remaining}/3 枠`,
      monthLabel: "表示月",
      dayCount: (count: number) => `${count} 件`,
      selectedDay: "選択日の予約",
      noPosts: "この日の予約はまだありません。",
      newPost: "New post",
      edit: "Edit",
      composeTitle: "投稿を予約",
      editTitle: "予約を編集",
      minLead: "5分以内不可",
      date: "日付",
      time: "時刻",
      timezone: "タイムゾーン",
      content: "投稿本文",
      placeholder: "Threadsへ投稿する本文を入力",
      confirm: "予約内容を確認",
      blocked: "現在は予約できません",
      full: "この日は予約上限の3件に達しています",
      missingDateTime: "投稿日時を選択してください",
      emptyContent: "投稿本文を入力してください",
      validTitle: "予約内容を確認します",
      outsideRange: "予約できるのは今日から30日以内です",
    },
    posts: {
      eyebrow: "Posts",
      title: "予約と投稿履歴",
      sort: "並び替え",
      newest: "新しい順",
      oldest: "古い順",
      status: "ステータス順",
      edit: "編集",
      delete: "削除",
      cloneFailed: "同じ本文で予約",
    },
    postStatus: {
      scheduled: "予約済み",
      posted: "投稿済み",
      failed: "失敗",
      canceled: "キャンセル済み",
    },
    analytics: {
      views: "閲覧",
      likes: "いいね",
      replies: "返信",
      reposts: "リポスト",
      quotes: "引用",
      shares: "シェア",
      engagement: "合計エンゲージメント",
      eyebrow: "Ranking",
      title: "反応が良かった投稿",
      cumulative: "累計値",
      noData: "分析データはまだありません。投稿後の分析取得が完了すると表示されます。",
      analyzedPosts: "分析済み投稿",
      latestStage: "最新取得",
    },
    settings: {
      eyebrow: "Account",
      title: "連携と状態",
      locale: "表示言語",
      timezone: "タイムゾーン",
      threads: "Threads連携",
      userStatus: "利用状態",
      billingStatus: "課金状態",
      trialPeriod: "トライアル期間",
      pauseNote: "休止: アカウントを残したまま、Stripeサブスクリプションを停止し、本アプリでの予約作成、投稿実行、分析取得を停止します。未投稿の予約はキャンセルされ、再開しても自動復活しません。再開後の利用には再登録が必要です。Threads本体の投稿は削除されません。",
      deleteNote: "退会: サブスクリプションを終了し、本アプリ上の未投稿予約をキャンセルし、投稿済み記録、投稿本文、分析データ、Threads連携情報を削除します。Threads本体の投稿は削除されません。",
      delete: "退会",
      legalEyebrow: "Legal",
      legalTitle: "法務文書",
      close: "閉じる",
      confirmTitle: "予約内容を確認",
      confirmEditTitle: "編集内容を確認",
      dateTime: "日時",
      body: "本文",
      back: "戻る",
      reserve: "予約する",
      update: "更新する",
      sending: "送信中...",
    },
    developer: {
      eyebrow: "Developer",
      title: "開発者画面",
      threadsId: "Threads ID",
      adminReview: "管理者確認",
      adminReviewBody: "Stripeキャンセル失敗など、手動確認が必要な退会ユーザーです。",
      loading: "読み込み中...",
      loadFailed: "開発者データの取得に失敗しました",
      totalUsers: "有効ユーザー",
      trialUsers: "トライアル",
      subscribedUsers: "サブスク",
      cvr: "CVR",
      reviewCount: "要確認",
      subscriptionsTotal: "サブスク記録",
      noReviewItems: "現在、管理者確認が必要なユーザーはいません。",
      user: "ユーザー",
      reason: "理由",
      stripeSubscription: "Stripe subscription",
      failedAt: "失敗日時",
      error: "エラー",
      resolve: "確認済みにする",
      resolveFailed: "管理者確認の更新に失敗しました",
    },
    legal: {
      commerce: "特定商取引法に基づく表記",
      terms: "利用規約",
      privacy: "プライバシーポリシー",
    },
    alerts: {
      saveSettingsFailed: "設定の保存に失敗しました",
      statusChangeFailed: "利用状態の変更に失敗しました",
      pauseConfirm: "休止するとStripeサブスクリプションを停止し、未投稿の予約はキャンセルされ、再開しても自動復活しません。再開後の利用には再登録が必要です。Threads本体の投稿は削除されません。休止しますか？",
      deleteConfirm: "退会すると本アプリ上の未投稿予約をキャンセルし、投稿済み記録、投稿本文、分析データ、Threads連携情報を削除します。Threads本体の投稿は削除されません。退会しますか？",
      deleteFailed: "退会処理に失敗しました",
      checkoutFailed: "Checkoutの開始に失敗しました",
      contentRequired: "投稿本文を入力してください",
      scheduleFailed: "予約に失敗しました",
      scheduled: "予約しました！",
      updated: "予約を更新しました！",
      deletePostConfirm: "この予約投稿を削除しますか？",
      postDeleteFailed: "削除に失敗しました",
    },
  },
  en: {
    loading: "Loading...",
    loginEyebrow: "Threads scheduler",
    loginLead: "Schedule Threads posts from a simple calendar.",
    loginButton: "Log in with Threads",
    trialOffer: "Free for 14 days. Then ¥390/month including tax.",
    loginLanguage: "Display language",
    loginHighlights: ["Schedule up to 30 days ahead", "Up to 3 scheduled posts per day", "Check basic analytics"],
    serviceSubtitle: "Threads scheduler",
    menuToggle: "Toggle menu",
    mainNav: "Main",
    logout: "Log out",
    nav: { calendar: "Schedule", posts: "Posts", analytics: "Analytics", settings: "Settings", developer: "Developer" },
    billing: {
      active: "Subscribed",
      activeBadge: "Subscription active",
      required: "Subscription required",
      trial: "Free trial",
      trialing: "In trial",
      trialExpired: "Trial ended",
      remaining: (days: number, hours: number) => `${days}d ${hours}h left`,
      period: (start: string, end: string) => `Start ${start} / End ${end}`,
      unset: "Not set",
      checkout: "Subscribe now",
      portal: "Update payment method",
      expiredTitle: "Your free trial has ended",
      expiredBody: (period: string) => `${period}. Scheduling, editing, publishing, and analytics require the ¥390/month plan.`,
    },
    notice: "For Meta App Review, this app uses only the minimum scopes needed for scheduling posts and basic analytics.",
    reconnect: {
      title: "Threads reconnect required",
      body: "Scheduling and publishing are paused until reconnect is completed.",
      button: "Reconnect",
      shortButton: "Reconnect",
      needed: "Reconnect required",
      enabled: "Connected",
    },
    paused: {
      title: "Account paused",
      body: "Resume is required before use. Scheduling and analytics are stopped while paused.",
      resume: "Resume",
      pause: "Pause",
      active: "Active",
      paused: "Paused",
    },
    calendar: {
      eyebrow: "Calendar",
      title: "Choose a date",
      slots: (remaining: number) => `${remaining}/3 slots`,
      monthLabel: "Month",
      dayCount: (count: number) => `${count} posts`,
      selectedDay: "Selected date",
      noPosts: "No scheduled posts for this date.",
      newPost: "New post",
      edit: "Edit",
      composeTitle: "Schedule a post",
      editTitle: "Edit schedule",
      minLead: "At least 5 minutes",
      date: "Date",
      time: "Time",
      timezone: "Time zone",
      content: "Post text",
      placeholder: "Write the text to post on Threads",
      confirm: "Review schedule",
      blocked: "Scheduling is currently unavailable",
      full: "This date has reached the 3-post limit",
      missingDateTime: "Choose a date and time",
      emptyContent: "Enter post text",
      validTitle: "Review the schedule",
      outsideRange: "Posts can be scheduled up to 30 days ahead",
    },
    posts: {
      eyebrow: "Posts",
      title: "Scheduled and posted",
      sort: "Sort",
      newest: "Newest",
      oldest: "Oldest",
      status: "Status",
      edit: "Edit",
      delete: "Delete",
      cloneFailed: "Schedule same text",
    },
    postStatus: {
      scheduled: "Scheduled",
      posted: "Posted",
      failed: "Failed",
      canceled: "Canceled",
    },
    analytics: {
      views: "Views",
      likes: "Likes",
      replies: "Replies",
      reposts: "Reposts",
      quotes: "Quotes",
      shares: "Shares",
      engagement: "Total engagement",
      eyebrow: "Ranking",
      title: "Top performing posts",
      cumulative: "Cumulative",
      noData: "No analytics data yet. Results appear after analytics collection completes for posted content.",
      analyzedPosts: "Analyzed posts",
      latestStage: "Latest stage",
    },
    settings: {
      eyebrow: "Account",
      title: "Connection and status",
      locale: "Display language",
      timezone: "Time zone",
      threads: "Threads connection",
      userStatus: "Account status",
      billingStatus: "Billing status",
      trialPeriod: "Trial period",
      pauseNote: "Pause: Keep the account but stop the Stripe subscription, scheduling, publishing, and analytics in this app. Pending schedules are canceled and will not be restored automatically after resume. Resuming use requires subscribing again. Posts already published on Threads are not deleted.",
      deleteNote: "Delete account: End the subscription, cancel this app's pending schedules, and delete posted records, post text, analytics data, and Threads connection data. Posts on Threads are not deleted.",
      delete: "Delete account",
      legalEyebrow: "Legal",
      legalTitle: "Legal documents",
      close: "Close",
      confirmTitle: "Review schedule",
      confirmEditTitle: "Review changes",
      dateTime: "Date and time",
      body: "Text",
      back: "Back",
      reserve: "Schedule",
      update: "Update",
      sending: "Sending...",
    },
    developer: {
      eyebrow: "Developer",
      title: "Developer screen",
      threadsId: "Threads ID",
      adminReview: "Admin review",
      adminReviewBody: "Deleted users that require manual review, such as failed Stripe cancellations.",
      loading: "Loading...",
      loadFailed: "Failed to load developer data",
      totalUsers: "Active users",
      trialUsers: "Trial",
      subscribedUsers: "Subscribed",
      cvr: "CVR",
      reviewCount: "Needs review",
      subscriptionsTotal: "Subscription records",
      noReviewItems: "No users currently require admin review.",
      user: "User",
      reason: "Reason",
      stripeSubscription: "Stripe subscription",
      failedAt: "Failed at",
      error: "Error",
      resolve: "Mark resolved",
      resolveFailed: "Failed to update admin review",
    },
    legal: {
      commerce: "Specified Commercial Transaction Act notice",
      terms: "Terms of Use",
      privacy: "Privacy Policy",
    },
    alerts: {
      saveSettingsFailed: "Failed to save settings",
      statusChangeFailed: "Failed to change account status",
      pauseConfirm: "Pausing will stop the Stripe subscription, cancel pending schedules, and they will not be restored automatically after resume. Resuming use requires subscribing again. Posts on Threads are not deleted. Continue?",
      deleteConfirm: "Deleting your account will cancel this app's pending schedules and remove posted records, post text, analytics data, and Threads connection data. Posts on Threads are not deleted. Continue?",
      deleteFailed: "Failed to delete account",
      checkoutFailed: "Failed to start Checkout",
      contentRequired: "Enter post text",
      scheduleFailed: "Failed to schedule",
      scheduled: "Scheduled.",
      updated: "Schedule updated.",
      deletePostConfirm: "Delete this scheduled post?",
      postDeleteFailed: "Failed to delete",
    },
  },
  zh: {} as never,
  fil: {} as never,
  vi: {} as never,
};

uiText.zh = {
  ...uiText.en,
  loginEyebrow: "Threads 预约工具",
  loginLead: "通过日历轻松预约 Threads 帖子。",
  loginButton: "使用 Threads 登录",
  trialOffer: "免费试用14天，之后每月390日元（含税）。",
  loginLanguage: "显示语言",
  loginHighlights: ["最多可预约30天后", "每天最多预约3条帖子", "查看基础分析"],
  mainNav: "主导航",
  logout: "退出登录",
  nav: { calendar: "预约", posts: "帖子", analytics: "分析", settings: "设置", developer: "开发者" },
  billing: {
    ...uiText.en.billing,
    active: "已订阅",
    activeBadge: "订阅有效",
    required: "需要订阅",
    trial: "免费试用",
    trialing: "试用中",
    trialExpired: "试用已结束",
    remaining: (days: number, hours: number) => `剩余${days}天 ${hours}小时`,
    period: (start: string, end: string) => `开始 ${start} / 结束 ${end}`,
    unset: "未设置",
    checkout: "立即订阅",
    expiredTitle: "免费试用已结束",
    expiredBody: (period: string) => `${period}。预约、编辑、发布和分析需要每月390日元的套餐。`,
  },
  notice: "为通过 Meta App Review，本应用仅使用预约投稿和基础分析所需的最小权限。",
  reconnect: { ...uiText.en.reconnect, title: "需要重新连接 Threads", body: "重新连接完成前，预约和发布将暂停。", button: "重新连接", shortButton: "重新连接", needed: "需要重新连接", enabled: "有效" },
  paused: { ...uiText.en.paused, title: "账户已休止", body: "需要恢复后才能使用。休止期间预约和分析会停止。", resume: "恢复", pause: "休止", active: "有效", paused: "休止中" },
  calendar: { ...uiText.en.calendar, title: "选择日期", monthLabel: "显示月份", selectedDay: "所选日期的预约", noPosts: "该日期还没有预约。", composeTitle: "预约帖子", editTitle: "编辑预约", date: "日期", time: "时间", timezone: "时区", content: "帖子内容", confirm: "确认预约", blocked: "当前无法预约", emptyContent: "请输入帖子内容" },
  posts: { ...uiText.en.posts, title: "预约与发布记录", sort: "排序", newest: "最新", oldest: "最旧", status: "状态", edit: "编辑", delete: "删除", cloneFailed: "用相同内容预约" },
  postStatus: { scheduled: "已预约", posted: "已发布", failed: "失败", canceled: "已取消" },
  analytics: { ...uiText.en.analytics, views: "浏览", likes: "赞", replies: "回复", reposts: "转发", quotes: "引用", shares: "分享", engagement: "总互动", title: "表现较好的帖子", cumulative: "累计" },
  settings: { ...uiText.en.settings, title: "连接与状态", locale: "显示语言", timezone: "时区", threads: "Threads连接", userStatus: "使用状态", billingStatus: "账单状态", trialPeriod: "试用期间", delete: "退会", legalTitle: "法律文件", close: "关闭", dateTime: "日期时间", body: "正文", back: "返回", reserve: "预约", update: "更新" },
  developer: { ...uiText.en.developer, title: "开发者页面", threadsId: "Threads ID", adminReview: "管理员确认" },
  legal: { commerce: "特定商业交易法标识", terms: "使用条款", privacy: "隐私政策" },
  alerts: { ...uiText.en.alerts, saveSettingsFailed: "设置保存失败", statusChangeFailed: "状态变更失败", deleteFailed: "退会处理失败", checkoutFailed: "Checkout启动失败", contentRequired: "请输入帖子内容", scheduleFailed: "预约失败", scheduled: "已预约。", updated: "预约已更新。", deletePostConfirm: "要删除这个预约吗？", postDeleteFailed: "删除失败" },
};

uiText.fil = {
  ...uiText.en,
  loginEyebrow: "Threads scheduler",
  loginLead: "Madaling mag-schedule ng Threads posts gamit ang calendar.",
  loginButton: "Mag-log in gamit ang Threads",
  trialOffer: "Libre sa loob ng 14 araw. Pagkatapos ay ¥390/buwan kasama ang tax.",
  loginLanguage: "Display language",
  loginHighlights: ["Mag-schedule hanggang 30 araw ahead", "Hanggang 3 scheduled posts bawat araw", "Tingnan ang basic analytics"],
  mainNav: "Pangunahing menu",
  logout: "Mag-log out",
  nav: { calendar: "Schedule", posts: "Posts", analytics: "Analytics", settings: "Settings", developer: "Developer" },
  billing: { ...uiText.en.billing, trial: "Free trial", trialing: "Nasa trial", checkout: "Mag-subscribe ngayon", remaining: (days: number, hours: number) => `${days} araw ${hours} oras pa`, period: (start: string, end: string) => `Simula ${start} / Wakas ${end}` },
  notice: "Para sa Meta App Review, minimum scopes lang ang ginagamit para sa scheduled posts at basic analytics.",
  reconnect: { ...uiText.en.reconnect, title: "Kailangan muling ikonekta ang Threads", body: "Naka-pause ang scheduling at publishing hanggang makumpleto ang reconnect.", button: "Reconnect", shortButton: "Reconnect", needed: "Kailangan reconnect", enabled: "Connected" },
  paused: { ...uiText.en.paused, title: "Naka-pause ang account", body: "Kailangang i-resume para magamit. Naka-stop ang scheduling at analytics habang naka-pause.", resume: "Resume", pause: "Pause", active: "Active", paused: "Paused" },
  calendar: { ...uiText.en.calendar, title: "Pumili ng petsa", monthLabel: "Buwan", selectedDay: "Napiling petsa", noPosts: "Wala pang scheduled posts sa petsang ito.", composeTitle: "Mag-schedule ng post", editTitle: "I-edit ang schedule", date: "Petsa", time: "Oras", timezone: "Time zone", content: "Post text", confirm: "Suriin ang schedule", blocked: "Hindi maaaring mag-schedule ngayon", emptyContent: "Ilagay ang post text" },
  posts: { ...uiText.en.posts, title: "Scheduled at posted", sort: "Ayusin", newest: "Pinakabago", oldest: "Pinakaluma", status: "Status", edit: "Edit", delete: "Delete", cloneFailed: "I-schedule ang parehong text" },
  postStatus: { scheduled: "Scheduled", posted: "Posted", failed: "Failed", canceled: "Canceled" },
  analytics: { ...uiText.en.analytics, views: "Views", likes: "Likes", replies: "Replies", reposts: "Reposts", quotes: "Quotes", shares: "Shares", engagement: "Total engagement", title: "Pinakamagandang posts", cumulative: "Cumulative" },
  settings: { ...uiText.en.settings, title: "Connection at status", locale: "Display language", timezone: "Time zone", threads: "Threads connection", userStatus: "Account status", billingStatus: "Billing status", trialPeriod: "Trial period", delete: "Delete account", legalTitle: "Legal documents", close: "Close", dateTime: "Petsa at oras", body: "Text", back: "Back", reserve: "Schedule", update: "Update" },
  developer: uiText.en.developer,
  legal: { commerce: "Commercial transaction notice", terms: "Terms of Use", privacy: "Privacy Policy" },
};

uiText.vi = {
  ...uiText.en,
  loginEyebrow: "Công cụ lên lịch Threads",
  loginLead: "Lên lịch bài đăng Threads dễ dàng bằng lịch.",
  loginButton: "Đăng nhập bằng Threads",
  trialOffer: "Miễn phí 14 ngày. Sau đó ¥390/tháng gồm thuế.",
  loginLanguage: "Ngôn ngữ hiển thị",
  loginHighlights: ["Lên lịch trước tối đa 30 ngày", "Tối đa 3 bài đã lên lịch mỗi ngày", "Xem phân tích cơ bản"],
  mainNav: "Điều hướng chính",
  logout: "Đăng xuất",
  nav: { calendar: "Lên lịch", posts: "Bài đăng", analytics: "Phân tích", settings: "Cài đặt", developer: "Developer" },
  billing: { ...uiText.en.billing, trial: "Dùng thử miễn phí", trialing: "Đang dùng thử", checkout: "Đăng ký ngay", remaining: (days: number, hours: number) => `Còn ${days} ngày ${hours} giờ`, period: (start: string, end: string) => `Bắt đầu ${start} / Kết thúc ${end}` },
  notice: "Để phục vụ Meta App Review, ứng dụng chỉ dùng các quyền tối thiểu cần cho lên lịch và phân tích cơ bản.",
  reconnect: { ...uiText.en.reconnect, title: "Cần kết nối lại Threads", body: "Lên lịch và đăng bài sẽ tạm dừng cho đến khi kết nối lại hoàn tất.", button: "Kết nối lại", shortButton: "Kết nối lại", needed: "Cần kết nối lại", enabled: "Đã kết nối" },
  paused: { ...uiText.en.paused, title: "Tài khoản đang tạm dừng", body: "Cần tiếp tục để sử dụng. Lên lịch và phân tích sẽ dừng khi tạm dừng.", resume: "Tiếp tục", pause: "Tạm dừng", active: "Hoạt động", paused: "Tạm dừng" },
  calendar: { ...uiText.en.calendar, title: "Chọn ngày", monthLabel: "Tháng", selectedDay: "Ngày đã chọn", noPosts: "Chưa có bài lên lịch cho ngày này.", composeTitle: "Lên lịch bài đăng", editTitle: "Sửa lịch", date: "Ngày", time: "Giờ", timezone: "Múi giờ", content: "Nội dung bài đăng", confirm: "Kiểm tra lịch", blocked: "Hiện không thể lên lịch", emptyContent: "Nhập nội dung bài đăng" },
  posts: { ...uiText.en.posts, title: "Đã lên lịch và đã đăng", sort: "Sắp xếp", newest: "Mới nhất", oldest: "Cũ nhất", status: "Trạng thái", edit: "Sửa", delete: "Xóa", cloneFailed: "Lên lịch cùng nội dung" },
  postStatus: { scheduled: "Đã lên lịch", posted: "Đã đăng", failed: "Thất bại", canceled: "Đã hủy" },
  analytics: { ...uiText.en.analytics, views: "Lượt xem", likes: "Thích", replies: "Trả lời", reposts: "Đăng lại", quotes: "Trích dẫn", shares: "Chia sẻ", engagement: "Tổng tương tác", title: "Bài đăng hiệu quả", cumulative: "Tổng cộng" },
  settings: { ...uiText.en.settings, title: "Kết nối và trạng thái", locale: "Ngôn ngữ hiển thị", timezone: "Múi giờ", threads: "Kết nối Threads", userStatus: "Trạng thái tài khoản", billingStatus: "Trạng thái thanh toán", trialPeriod: "Thời gian dùng thử", delete: "Xóa tài khoản", legalTitle: "Tài liệu pháp lý", close: "Đóng", dateTime: "Ngày giờ", body: "Nội dung", back: "Quay lại", reserve: "Lên lịch", update: "Cập nhật" },
  developer: uiText.en.developer,
  legal: { commerce: "Thông báo giao dịch thương mại", terms: "Điều khoản sử dụng", privacy: "Chính sách quyền riêng tư" },
};

const legalDocuments: Record<LegalDocument, { heading: string; title: string }> = {
  commerce: {
    heading: "## 特定商取引法に基づく表記",
    title: "特定商取引法に基づく表記",
  },
  terms: {
    heading: "## 利用規約",
    title: "利用規約",
  },
  privacy: {
    heading: "## プライバシーポリシー",
    title: "プライバシーポリシー",
  },
};

function initialLocale(): LocaleCode {
  if (typeof window === "undefined") return "ja";
  const storedLocale = window.localStorage.getItem("s4s_locale");
  return localeLabels.find((item) => item.code === storedLocale)?.code ?? "ja";
}

const statusMeta: Record<PostStatus, { label: string; icon: typeof Clock3; tone: string }> = {
  scheduled: { label: "予約済み", icon: Clock3, tone: "info" },
  posted: { label: "投稿済み", icon: CheckCircle2, tone: "success" },
  failed: { label: "失敗", icon: XCircle, tone: "danger" },
  canceled: { label: "キャンセル済み", icon: PauseCircle, tone: "muted" }
};

function toScheduledPost(item: ApiScheduledPost): ScheduledPost {
  const scheduledAt = new Date(item.scheduled_at);
  const validStatuses: PostStatus[] = ["scheduled", "posted", "failed", "canceled"];

  return {
    id: item.post_id,
    content: item.content,
    date: scheduledAt.toLocaleDateString("sv-SE"),
    time: scheduledAt.toLocaleTimeString("sv-SE", {
      hour: "2-digit",
      minute: "2-digit",
      hour12: false,
    }),
    timezone: item.timezone ?? "Asia/Tokyo",
    status: validStatuses.includes(item.status as PostStatus) ? item.status as PostStatus : "scheduled",
    failureReason: item.failure_reason ?? "",
    analyticsStage: item.analytics_stage ?? "",
    analyticsFetchedAt: item.analytics_fetched_at ?? 0,
    metrics: item.metrics,
  };
}

function App() {
  const apiBaseUrl = import.meta.env.VITE_API_BASE_URL;
  const appUrl = (import.meta.env.VITE_APP_URL as string | undefined)?.replace(/\/$/, "");
  const clarityProjectId = import.meta.env.VITE_CLARITY_PROJECT_ID as string | undefined;

  const handleThreadsLogin = () => {
    const returnTo = appUrl || window.location.origin;
  
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
  const [needsReconnect, setNeedsReconnect] = useState(false);
  const [isDeveloper, setIsDeveloper] = useState(false);
  const [developerDashboard, setDeveloperDashboard] = useState<DeveloperDashboard | null>(null);
  const [developerLoading, setDeveloperLoading] = useState(false);
  const [developerError, setDeveloperError] = useState("");
  const [selectedLegalDocument, setSelectedLegalDocument] = useState<LegalDocument | null>(null);
  const [locale, setLocale] = useState<string>(initialLocale);
  const copy = uiText[locale as LocaleCode] ?? uiText.ja;
  const [subscriptionStatus, setSubscriptionStatus] = useState<SubscriptionStatus>("trialing");
  const [trialStartedAt, setTrialStartedAt] = useState<number | null>(null);
  const [trialEnd, setTrialEnd] = useState<number | null>(null);
  const [hasSubscriptionEntitlement, setHasSubscriptionEntitlement] = useState(true);
  const canStartCheckout = subscriptionStatus !== "active";
  const userTimezone =
    Intl.DateTimeFormat().resolvedOptions().timeZone || "Asia/Tokyo";
  const [settingsTimezone, setSettingsTimezone] = useState(userTimezone);
  const [now, setNow] = useState(() => new Date());
  const headerDate = formatHeaderDate(now, settingsTimezone, copy);
  const defaultDateTime = new Date();
  defaultDateTime.setMinutes(defaultDateTime.getMinutes() + 10);

  const today = defaultDateTime.toLocaleDateString("sv-SE");
  const currentTime = defaultDateTime.toLocaleTimeString("sv-SE", {
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
  const currentMonth = today.slice(0, 7);

  useEffect(() => {
    const timer = window.setInterval(() => {
      setNow(new Date());
    }, 60_000);
    return () => window.clearInterval(timer);
  }, []);

  const [selectedDate, setSelectedDate] = useState(today);
  const [visibleMonth, setVisibleMonth] = useState(currentMonth);

  const [posts, setPosts] = useState<ScheduledPost[]>([]);
  const [draft, setDraft] = useState({
    date: today,
    time: currentTime,
    timezone: userTimezone,
    content: ""
  });
  const [editingId, setEditingId] = useState<string | null>(null);
  const [showConfirm, setShowConfirm] = useState(false);
  const [isPreparingConfirm, setIsPreparingConfirm] = useState(false);
  const [isSavingDraft, setIsSavingDraft] = useState(false);

  const handleThreadsReconnect = () => {
    const returnTo = window.location.origin;
    window.location.href =
      `${apiBaseUrl}/auth/threads/start?reauth=1&return_to=${encodeURIComponent(returnTo)}`;
  };

  const saveSettings = async (nextLocale = locale, nextTimezone = settingsTimezone) => {
    const res = await fetch(`${apiBaseUrl}/me/settings`, {
      method: "PATCH",
      credentials: "include",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        locale: nextLocale,
        timezone: nextTimezone,
      }),
    });

    const data = await res.json();
    if (!res.ok) {
      alert(data.message ?? copy.alerts.saveSettingsFailed);
      return;
    }

    setLocale(data.locale);
    window.localStorage.setItem("s4s_locale", data.locale);
    setSettingsTimezone(data.timezone);
    setDraft((current) => ({ ...current, timezone: data.timezone }));
  };

  const changeLoginLocale = (nextLocale: string) => {
    setLocale(nextLocale);
    window.localStorage.setItem("s4s_locale", nextLocale);
  };

  const changeAccountStatus = async (nextStatus: "active" | "paused") => {
    if (nextStatus === "paused") {
      const confirmed = window.confirm(copy.alerts.pauseConfirm);
      if (!confirmed) return;
    }

    const endpoint = nextStatus === "paused" ? "/account/pause" : "/account/resume";
    const res = await fetch(`${apiBaseUrl}${endpoint}`, {
      method: "POST",
      credentials: "include",
    });

    const data = await res.json();
    if (!res.ok) {
      alert(data.message ?? copy.alerts.statusChangeFailed);
      return;
    }

    setUserStatus(data.user_status);
    if (data.subscription_status) {
      setSubscriptionStatus(data.subscription_status);
    }
    if (typeof data.has_subscription_entitlement === "boolean") {
      setHasSubscriptionEntitlement(data.has_subscription_entitlement);
    }
    await fetchScheduledPosts();
  };

  const deleteAccount = async () => {
    const confirmed = window.confirm(copy.alerts.deleteConfirm);
    if (!confirmed) return;

    const res = await fetch(`${apiBaseUrl}/account`, {
      method: "DELETE",
      credentials: "include",
    });

    const data = await res.json();
    if (!res.ok) {
      alert(data.message ?? copy.alerts.deleteFailed);
      return;
    }

    window.location.reload();
  };

  const startCheckout = async () => {
    const res = await fetch(`${apiBaseUrl}/billing/checkout`, {
      method: "POST",
      credentials: "include",
    });

    const data = await res.json();
    if (!res.ok) {
      alert(data.message ?? copy.alerts.checkoutFailed);
      return;
    }

    window.location.href = data.checkout_url;
  };

  const openBillingPortal = async () => {
    const res = await fetch(`${apiBaseUrl}/billing/portal`, {
      method: "POST",
      credentials: "include",
    });

    const data = await res.json();
    if (!res.ok) {
      alert(data.message ?? copy.alerts.checkoutFailed);
      return;
    }

    window.location.href = data.portal_url;
  };

  const fetchDeveloperDashboard = useCallback(async () => {
    if (!isDeveloper) return;

    setDeveloperLoading(true);
    setDeveloperError("");

    try {
      const res = await fetch(`${apiBaseUrl}/developer/dashboard`, {
        credentials: "include",
      });
      const data = await res.json();

      if (!res.ok) {
        setDeveloperError(data.message ?? copy.developer.loadFailed);
        return;
      }

      setDeveloperDashboard(data);
    } catch {
      setDeveloperError(copy.developer.loadFailed);
    } finally {
      setDeveloperLoading(false);
    }
  }, [apiBaseUrl, copy.developer.loadFailed, isDeveloper]);

  const resolveAdminReview = useCallback(async (appUserId: string) => {
    const res = await fetch(`${apiBaseUrl}/developer/admin-review/resolve`, {
      method: "POST",
      credentials: "include",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ app_user_id: appUserId }),
    });
    const data = await res.json();

    if (!res.ok) {
      alert(data.message ?? copy.developer.resolveFailed);
      return;
    }

    await fetchDeveloperDashboard();
  }, [apiBaseUrl, copy.developer.resolveFailed, fetchDeveloperDashboard]);

  const selectedPosts = posts.filter(
    (post) => post.date === selectedDate && post.status === "scheduled"
  );
  
  const targetDatePosts = posts.filter(
    (post) =>
      post.date === draft.date &&
      post.status === "scheduled" &&
      post.id !== editingId
  );
  
  const remainingSlots = Math.max(0, 3 - targetDatePosts.length);
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
  const displaySubscriptionStatus = subscriptionStatus;
  const hasEffectiveSubscriptionEntitlement =
    hasSubscriptionEntitlement || subscriptionStatus === "active";
  const isBlocked = userStatus !== "active" || needsReconnect || !hasEffectiveSubscriptionEntitlement;
  
  const [isLoggedIn, setIsLoggedIn] = useState<boolean | null>(null);

  const fetchScheduledPosts = useCallback(async () => {
    const res = await fetch(`${apiBaseUrl}/scheduled-posts`, {
      credentials: "include",
    });
  
    const data = await res.json();
  
    if (!res.ok) {
      console.log("SCHEDULE LIST ERROR", data);
      return;
    }
  
    setPosts((data.items ?? []).map(toScheduledPost));
  }, [apiBaseUrl]);

  useEffect(() => {
    fetch(`${apiBaseUrl}/me`, {
      credentials: "include",
    })
      .then(async (res) => {
        if (!res.ok) {
          setIsLoggedIn(false);
          return;
        }
  
        const data = await res.json();
        setIsLoggedIn(true);
  
        console.log("ME RESULT", data);
  
        setNeedsReconnect(Boolean(data.needs_reconnect ?? data.needsReconnect ?? false));
        setIsDeveloper(Boolean(data.is_developer ?? data.isDeveloper ?? false));
        setUserStatus((data.user_status ?? data.userStatus ?? "active").toLowerCase());
        setSubscriptionStatus(data.subscription_status ?? "trialing");
        setTrialStartedAt(data.trial_started_at ?? null);
        setTrialEnd(data.trial_end ?? null);
        setHasSubscriptionEntitlement(Boolean(data.has_subscription_entitlement ?? false));
        setLocale(data.locale ?? "ja");
        window.localStorage.setItem("s4s_locale", data.locale ?? "ja");
        setSettingsTimezone(data.timezone ?? userTimezone);
        setDraft((current) => ({
          ...current,
          timezone: data.timezone ?? current.timezone,
        }));
  
        await fetchScheduledPosts();
      })
      .catch(() => {
        setIsLoggedIn(false);
      });
  }, [apiBaseUrl, fetchScheduledPosts, userTimezone]);

  useEffect(() => {
    if (isLoggedIn !== false || !clarityProjectId) return;
    if (document.querySelector(`script[data-clarity-project-id="${clarityProjectId}"]`)) return;

    const clarityWindow = window as unknown as {
      clarity?: (...args: unknown[]) => void;
    };

    clarityWindow.clarity = clarityWindow.clarity || function (...args: unknown[]) {
      const queuedClarity = clarityWindow.clarity as unknown as { q?: unknown[] };
      queuedClarity.q = queuedClarity.q || [];
      queuedClarity.q.push(args);
    };

    const script = document.createElement("script");
    script.async = true;
    script.dataset.clarityProjectId = clarityProjectId;
    script.src = `https://www.clarity.ms/tag/${clarityProjectId}`;
    document.head.appendChild(script);
  }, [clarityProjectId, isLoggedIn]);

  useEffect(() => {
    if (isDeveloper && view === "developer" && !developerDashboard && !developerLoading) {
      void fetchDeveloperDashboard();
    }
  }, [developerDashboard, developerLoading, fetchDeveloperDashboard, isDeveloper, view]);

  function resetDraft() {
    const nextDateTime = new Date();
    nextDateTime.setMinutes(nextDateTime.getMinutes() + 10);

    const nextDate = nextDateTime.toLocaleDateString("sv-SE");
    const nextTime = nextDateTime.toLocaleTimeString("sv-SE", {
      hour: "2-digit",
      minute: "2-digit",
      hour12: false,
    });

    setDraft({
      date: nextDate,
      time: nextTime,
      timezone: userTimezone,
      content: ""
    });
  }

  function beginEdit(post: ScheduledPost) {
    setShowConfirm(false);
    setIsPreparingConfirm(false);
    setEditingId(post.id);
    setDraft({
      date: post.date,
      time: post.time,
      timezone: post.timezone,
      content: post.content
    });
    setView("calendar");
  }

  function openConfirmDialog() {
    if (isPreparingConfirm || showConfirm) return;

    setIsPreparingConfirm(true);
    window.setTimeout(() => {
      setShowConfirm(true);
      setIsPreparingConfirm(false);
    }, 0);
  }

  async function saveDraft() {
    if (isSavingDraft) return;

    if (!draft.content.trim()) {
      alert(copy.alerts.contentRequired);
      return;
    }

    setIsSavingDraft(true);

    try {
      const scheduledAt = new Date(`${draft.date}T${draft.time}:00`).toISOString();

      const url = editingId
        ? `${apiBaseUrl}/scheduled-posts/${editingId}`
        : `${apiBaseUrl}/scheduled-posts`;

      const method = editingId ? "PUT" : "POST";

      const res = await fetch(url, {
        method,
        credentials: "include",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          content: draft.content.trim(),
          scheduled_at: scheduledAt,
          timezone: draft.timezone,
        }),
      });

      const data = await res.json();
      console.log("SCHEDULE RESULT", data);

      if (!res.ok) {
        alert(data.message || copy.alerts.scheduleFailed);
        return;
      }

      const saved = data.post;

      if (editingId) {
        setPosts((current) =>
          current.map((post) =>
            post.id === editingId
              ? {
                  ...post,
                  content: saved.content,
                  date: draft.date,
                  time: draft.time,
                  timezone: saved.timezone,
                  status: "scheduled",
                }
              : post
          )
        );
      } else {
        setPosts((current) => [
          {
            id: saved.post_id,
            content: saved.content,
            date: draft.date,
            time: draft.time,
            timezone: saved.timezone,
            status: "scheduled",
          },
          ...current,
        ]);
      }

      setSelectedDate(draft.date);
      setEditingId(null);
      setShowConfirm(false);
      resetDraft();
      alert(editingId ? copy.alerts.updated : copy.alerts.scheduled);
    } finally {
      setIsSavingDraft(false);
    }
  }

  async function deletePost(id: string) {
    const confirmed = window.confirm(copy.alerts.deletePostConfirm);
  
    if (!confirmed) {
      return;
    }
  
    const res = await fetch(`${apiBaseUrl}/scheduled-posts/${id}`, {
      method: "DELETE",
      credentials: "include",
    });
  
    const data = await res.json();
  
    if (!res.ok) {
      alert(data.message ?? copy.alerts.postDeleteFailed);
      return;
    }
  
    setPosts((current) => current.filter((post) => post.id !== id));

    if (editingId === id) {
      setEditingId(null);
      setShowConfirm(false);
      setIsPreparingConfirm(false);
      resetDraft();
    }
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
    return (
      <div className="loading-page">
        <div className="loading-panel">
          <div className="brand-lockup">
            <div className="brand-mark">S4S</div>
            <div>
              <strong>Schedule For SNS</strong>
              <span>{copy.loading}</span>
            </div>
          </div>
          <div className="loading-bar" aria-hidden="true" />
        </div>
      </div>
    );
  }

  if (!isLoggedIn) {
    return (
      <div className="login-page">
        <div className="login-shell">
          <div className="login-copy">
            <div className="brand-lockup login-brand">
              <div className="brand-mark">S4S</div>
              <div>
                <strong>Schedule For SNS</strong>
                <span>{copy.loginEyebrow}</span>
              </div>
            </div>
            <h1>Schedule For SNS</h1>
            <p>{copy.loginLead}</p>
            <div className="login-highlights">
              {copy.loginHighlights.map((item: string) => (
                <span key={item}>{item}</span>
              ))}
            </div>
          </div>

          <div className="login-card">
            <LanguagePills copy={copy} locale={locale} onChange={changeLoginLocale} />

            <button className="button primary login-button" onClick={handleThreadsLogin}>
              {copy.loginButton}
            </button>

            <p className="muted-text">{copy.trialOffer}</p>

            <div className="login-legal-links" aria-label={copy.settings.legalTitle}>
              <button type="button" onClick={() => setSelectedLegalDocument("commerce")}>
                {copy.legal.commerce}
              </button>
              <button type="button" onClick={() => setSelectedLegalDocument("terms")}>
                {copy.legal.terms}
              </button>
              <button type="button" onClick={() => setSelectedLegalDocument("privacy")}>
                {copy.legal.privacy}
              </button>
            </div>
          </div>
        </div>
        {selectedLegalDocument && (
          <LegalDocumentDialog
            copy={copy}
            document={selectedLegalDocument}
            onClose={() => setSelectedLegalDocument(null)}
          />
        )}
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
            <span>{copy.serviceSubtitle}</span>
          </div>
        </div>

        <div className="mobile-header-actions">
          <div className="mobile-trial-chip">
            <Clock3 size={15} />
            <span>{billingLabel(displaySubscriptionStatus, trialEnd, copy)}</span>
          </div>
          <button
            aria-expanded={menuOpen}
            aria-label={copy.menuToggle}
            className="hamburger-button"
            onClick={() => setMenuOpen((open) => !open)}
          >
            <Menu size={22} />
          </button>
        </div>

        <nav className={`nav-stack ${menuOpen ? "open" : ""}`} aria-label={copy.mainNav}>
          <NavButton active={view === "calendar"} icon={CalendarDays} label={copy.nav.calendar} onClick={() => { setView("calendar"); setMenuOpen(false); }} />
          <NavButton active={view === "posts"} icon={FileText} label={copy.nav.posts} onClick={() => { setView("posts"); setMenuOpen(false); }} />
          <NavButton active={view === "analytics"} icon={BarChart3} label={copy.nav.analytics} onClick={() => { setView("analytics"); setMenuOpen(false); }} />
          <NavButton active={view === "settings"} icon={Settings} label={copy.nav.settings} onClick={() => { setView("settings"); setMenuOpen(false); }} />
          {isDeveloper && (
            <NavButton active={view === "developer"} icon={Wrench} label={copy.nav.developer} onClick={() => { setView("developer"); setMenuOpen(false); }} />
          )}
        </nav>

        <div className="trial-panel">
          <span>{displaySubscriptionStatus === "active" ? copy.billing.activeBadge : copy.billing.trial}</span>
          <strong>{billingLabel(displaySubscriptionStatus, trialEnd, copy)}</strong>
          <small>{trialPeriodLabel(trialStartedAt, trialEnd, copy)}</small>
          {canStartCheckout && (
            <button className="button secondary" onClick={() => void startCheckout()}>
              {copy.billing.checkout}
            </button>
          )}
        </div>
      </aside>

      <main className="main-surface">
        <header className="topbar">
          <div>
            <p className="eyebrow">{headerDate}</p>
            <h1>{viewTitle(view, copy)}</h1>
          </div>
          <div className="topbar-actions">
            <button
              className="icon-button"
              title={copy.logout}
              onClick={handleLogout}
            >
              <LogOut size={18} />
            </button>
          </div>
        </header>

        {!hasEffectiveSubscriptionEntitlement && (
          <section className="dialog-banner danger">
            <CreditCard size={20} />
            <div>
              <strong>{copy.billing.expiredTitle}</strong>
              <span>{copy.billing.expiredBody(trialPeriodLabel(trialStartedAt, trialEnd, copy))}</span>
            </div>
            <button className="button dark" onClick={() => void startCheckout()}>
              {copy.billing.checkout}
            </button>
          </section>
        )}

        {needsReconnect && (
          <section className="dialog-banner danger">
            <AlertTriangle size={20} />
            <div>
              <strong>{copy.reconnect.title}</strong>
              <span>{copy.reconnect.body}</span>
            </div>
            <button className="button dark" onClick={handleThreadsReconnect}>
              <RefreshCcw size={16} />
              {copy.reconnect.button}
            </button>
          </section>
        )}

        {userStatus === "paused" && (
          <section className="dialog-banner">
            <PauseCircle size={20} />
            <div>
              <strong>{copy.paused.title}</strong>
              <span>{copy.paused.body}</span>
            </div>
            <button className="button dark" onClick={() => void changeAccountStatus("active")}>
              {copy.paused.resume}
            </button>
          </section>
        )}

        {view === "calendar" && (
          <CalendarView
            activePosts={activePosts}
            draft={draft}
            editingId={editingId}
            isPreparingConfirm={isPreparingConfirm}
            isBlocked={isBlocked}
            onRequestConfirm={openConfirmDialog}
            copy={copy}
            remainingSlots={remainingSlots}
            selectedDate={selectedDate}
            selectedPosts={selectedPosts}
            setDraft={setDraft}
            setSelectedDate={setSelectedDate}
            setVisibleMonth={setVisibleMonth}
            visibleMonth={visibleMonth}
          />
        )}

        {view === "posts" && (
          <PostsView copy={copy} posts={posts} onCloneFailed={cloneFailed} onDelete={deletePost} onEdit={beginEdit} />
        )}

        {view === "analytics" && <AnalyticsView analytics={analytics} copy={copy} engagement={engagement} postedPosts={postedPosts} />}

        {view === "settings" && (
          <SettingsView
            locale={locale}
            needsReconnect={needsReconnect}
            onDeleteAccount={deleteAccount}
            onOpenBillingPortal={openBillingPortal}
            onOpenLegalDocument={setSelectedLegalDocument}
            onReconnect={handleThreadsReconnect}
            onSaveSettings={saveSettings}
            onStartCheckout={startCheckout}
            onStatusChange={changeAccountStatus}
            setLocale={setLocale}
            setSettingsTimezone={setSettingsTimezone}
            settingsTimezone={settingsTimezone}
            canStartCheckout={canStartCheckout}
            copy={copy}
            subscriptionStatus={displaySubscriptionStatus}
            trialStartedAt={trialStartedAt}
            trialEnd={trialEnd}
            userStatus={userStatus}
          />
        )}

        {isDeveloper && view === "developer" && (
          <DeveloperView
            copy={copy}
            dashboard={developerDashboard}
            error={developerError}
            isLoading={developerLoading}
            onRefresh={fetchDeveloperDashboard}
            onResolveReview={resolveAdminReview}
          />
        )}
      </main>

      {showConfirm && (
        <ConfirmDialog
          draft={draft}
          editingId={editingId}
          copy={copy}
          isSubmitting={isSavingDraft}
          onCancel={() => setShowConfirm(false)}
          onConfirm={saveDraft}
        />
      )}
      {selectedLegalDocument && (
        <LegalDocumentDialog
          copy={copy}
          document={selectedLegalDocument}
          onClose={() => setSelectedLegalDocument(null)}
        />
      )}
    </div>
  );
}

function viewTitle(view: View, copy: typeof uiText.ja) {
  return copy.nav[view];
}

function formatHeaderDate(date: Date, timeZone: string, copy: typeof uiText.ja) {
  const dateText = new Intl.DateTimeFormat(localeToDateFormat(copy), {
    year: "numeric",
    month: "long",
    day: "numeric",
    timeZone,
  }).format(date);
  const weekday = new Intl.DateTimeFormat(localeToDateFormat(copy), {
    weekday: "long",
    timeZone,
  }).format(date);
  return `${dateText} ${weekday}`;
}

function billingLabel(status: SubscriptionStatus, trialEnd: number | null, copy: typeof uiText.ja) {
  if (status === "active") return copy.billing.active;
  if (status === "trial_expired") return copy.billing.trialExpired;
  if (status !== "trialing") return copy.billing.required;
  if (!trialEnd) return copy.billing.trialing;

  const remainingSeconds = Math.max(0, trialEnd - Math.floor(Date.now() / 1000));
  if (remainingSeconds <= 0) return copy.billing.trialExpired;

  const days = Math.floor(remainingSeconds / 86400);
  const hours = Math.floor((remainingSeconds % 86400) / 3600);
  return copy.billing.remaining(days, hours);
}

function billingStatusLabel(status: SubscriptionStatus, copy: typeof uiText.ja) {
  if (status === "active") return copy.billing.active;
  if (status === "trialing") return copy.billing.trialing;
  if (status === "trial_expired") return copy.billing.trialExpired;
  return copy.billing.required;
}

function formatUnixDate(timestamp: number | null, copy: typeof uiText.ja) {
  if (!timestamp) return copy.billing.unset;
  return new Intl.DateTimeFormat(localeToDateFormat(copy), {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(timestamp * 1000));
}

function trialPeriodLabel(startedAt: number | null, trialEnd: number | null, copy: typeof uiText.ja) {
  return copy.billing.period(formatUnixDate(startedAt, copy), formatUnixDate(trialEnd, copy));
}

function localeToDateFormat(copy: typeof uiText.ja) {
  if (copy === uiText.ja) return "ja-JP";
  if (copy === uiText.zh) return "zh-CN";
  if (copy === uiText.vi) return "vi-VN";
  if (copy === uiText.fil) return "fil-PH";
  return "en-US";
}

function LanguagePills({
  copy,
  locale,
  onChange
}: {
  copy: typeof uiText.ja;
  locale: string;
  onChange: (locale: string) => void;
}) {
  return (
    <div className="language-panel" aria-label={copy.loginLanguage}>
      <span>{copy.loginLanguage}</span>
      <div className="language-pills">
        {localeLabels.map((item) => (
          <button
            className={`language-pill ${locale === item.code ? "active" : ""}`}
            key={item.code}
            onClick={() => onChange(item.code)}
            type="button"
          >
            <span aria-hidden="true">{item.flag}</span>
            {item.label}
          </button>
        ))}
      </div>
    </div>
  );
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
  copy,
  draft,
  editingId,
  isPreparingConfirm,
  isBlocked,
  onRequestConfirm,
  remainingSlots,
  selectedDate,
  selectedPosts,
  setDraft,
  setSelectedDate,
  setVisibleMonth,
  visibleMonth
}: {
  activePosts: ScheduledPost[];
  copy: typeof uiText.ja;
  draft: { date: string; time: string; timezone: string; content: string };
  editingId: string | null;
  isPreparingConfirm: boolean;
  isBlocked: boolean;
  onRequestConfirm: () => void;
  remainingSlots: number;
  selectedDate: string;
  selectedPosts: ScheduledPost[];
  setDraft: (draft: { date: string; time: string; timezone: string; content: string }) => void;
  setSelectedDate: (date: string) => void;
  setVisibleMonth: (month: string) => void;
  visibleMonth: string;
}) {
  const dates = useMemo(() => buildMonthDates(visibleMonth), [visibleMonth]);
  const dateGridRef = useRef<HTMLDivElement | null>(null);
  const isFull = remainingSlots === 0 && !editingId;
  const isContentEmpty = draft.content.trim().length === 0;
  const isDateTimeMissing = !draft.date || !draft.time;
  const minDate = getTodayDate();
  const maxDate = getMaxReservableDate();

  const submitDisabledReason = (() => {
    if (isBlocked) return copy.calendar.blocked;
    if (isFull) return copy.calendar.full;
    if (isDateTimeMissing) return copy.calendar.missingDateTime;
    if (isContentEmpty) return copy.calendar.emptyContent;
    return "";
  })();

  const canSubmit = submitDisabledReason === "";

  useEffect(() => {
    const today = getTodayDate();
    if (!today.startsWith(visibleMonth)) return;

    const grid = dateGridRef.current;
    const todayButton = grid?.querySelector<HTMLButtonElement>(`button[data-date="${today}"]`);
    if (!grid || !todayButton) return;

    grid.scrollLeft = todayButton.offsetLeft - (grid.clientWidth / 2) + (todayButton.clientWidth / 2);
  }, [visibleMonth, dates]);

  return (
    <div className="workspace-grid">
      <section className="panel calendar-panel">
        <div className="section-heading">
          <div>
            <p className="eyebrow">{copy.calendar.eyebrow}</p>
            <h2>{copy.calendar.title}</h2>
          </div>
          <span className="pill">{copy.calendar.slots(remainingSlots)}</span>
        </div>
        <div className="month-controls">
          <label>
            {copy.calendar.monthLabel}
            <select
              value={visibleMonth}
              onChange={(event) => setVisibleMonth(event.target.value)}
            >
              {buildReservableMonths().map((value) => (
                <option key={value} value={value}>
                  {formatMonthLabel(value, copy)}
                </option>
              ))}
            </select>
          </label>
        </div>
        <div className="date-grid" ref={dateGridRef}>
        {dates.map((date) => {
          const count = activePosts.filter((post) => post.date === date).length;
          const isOutOfRange = date < minDate || date > maxDate;
          const isFullDate = count >= 3 && date !== draft.date;
          const isDisabledDate = isOutOfRange || isFullDate;

          return (
            <button
              className={`date-cell ${selectedDate === date ? "selected" : ""} ${
                isDisabledDate ? "disabled" : ""
              }`}
              key={date}
              data-date={date}
              disabled={isDisabledDate}
              onClick={() => {
                setSelectedDate(date);
                setDraft({ ...draft, date });
              }}
              title={
                isOutOfRange
                  ? copy.calendar.outsideRange
                  : isFullDate
                    ? copy.calendar.full
                    : ""
              }
            >
              <strong>{date.slice(8)}</strong>
              <span>{weekdayLabel(date, copy)}</span>
              <small>{copy.calendar.dayCount(count)}</small>
            </button>
          );
        })}
        </div>
        <div className="day-list">
          <h3>{copy.calendar.selectedDay}</h3>
          {selectedPosts.length === 0 ? (
            <p className="muted-text">{copy.calendar.noPosts}</p>
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
            <p className="eyebrow">{editingId ? copy.calendar.edit : copy.calendar.newPost}</p>
            <h2>{editingId ? copy.calendar.editTitle : copy.calendar.composeTitle}</h2>
          </div>
          <span className="pill muted">{copy.calendar.minLead}</span>
        </div>
        <div className="form-grid">
          <label>
            {copy.calendar.date}
            <input
              type="date"
              min={getTodayDate()}
              max={getMaxReservableDate()}
              value={draft.date}
              onChange={(event) => setDraft({ ...draft, date: event.target.value })}
            />
          </label>
          <label>
            {copy.calendar.time}
            <input type="time" value={draft.time} onChange={(event) => setDraft({ ...draft, time: event.target.value })} />
          </label>
          <label className="wide">
            {copy.calendar.timezone}
            <select value={draft.timezone} onChange={(event) => setDraft({ ...draft, timezone: event.target.value })}>
              <option value="Asia/Tokyo">Asia/Tokyo</option>
              <option value="America/Los_Angeles">America/Los_Angeles</option>
              <option value="Europe/London">Europe/London</option>
              <option value="Asia/Manila">Asia/Manila</option>
              <option value="Asia/Ho_Chi_Minh">Asia/Ho_Chi_Minh</option>
            </select>
          </label>
          <label className="wide">
            {copy.calendar.content}
            <textarea
              maxLength={500}
              placeholder={copy.calendar.placeholder}
              value={draft.content}
              onChange={(event) => setDraft({ ...draft, content: event.target.value })}
            />
          </label>
        </div>
        <div className="composer-footer">
          <span>{draft.content.length}/500</span>
          <button
            className="button primary"
            disabled={!canSubmit || isPreparingConfirm}
            onClick={onRequestConfirm}
            title={submitDisabledReason || copy.calendar.validTitle}
          >
            {isPreparingConfirm ? copy.settings.sending : copy.calendar.confirm}
          </button>
          {!canSubmit && (
            <p className="form-hint error">
              {submitDisabledReason}
            </p>
          )}
        </div>
      </section>
    </div>
  );
}

function PostsView({
  copy,
  posts,
  onCloneFailed,
  onDelete,
  onEdit
}: {
  copy: typeof uiText.ja;
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
          <p className="eyebrow">{copy.posts.eyebrow}</p>
          <h2>{copy.posts.title}</h2>
        </div>
        <label className="sort-control">
          {copy.posts.sort}
          <select value={sort} onChange={(event) => setSort(event.target.value as PostSort)}>
            <option value="newest">{copy.posts.newest}</option>
            <option value="oldest">{copy.posts.oldest}</option>
            <option value="status">{copy.posts.status}</option>
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
                  <strong>{copy.postStatus[post.status]}</strong>
                </div>
                <p>{post.content}</p>
                {post.failureReason && <small className="failure-text">{post.failureReason}</small>}
              </div>
              <div className="row-actions">
                {post.status === "scheduled" && (
                  <>
                    <button className="icon-button" title={copy.posts.edit} onClick={() => onEdit(post)}>
                      <Edit3 size={17} />
                    </button>
                    <button className="icon-button" title={copy.posts.delete} onClick={() => onDelete(post.id)}>
                      <Trash2 size={17} />
                    </button>
                  </>
                )}
                {post.status === "failed" && (
                  <button className="button secondary" onClick={() => onCloneFailed(post)}>
                    <RefreshCcw size={16} />
                    {copy.posts.cloneFailed}
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

function buildReservableMonths() {
  const today = new Date();
  today.setHours(0, 0, 0, 0);

  const maxDate = new Date(today);
  maxDate.setDate(today.getDate() + 30);

  const months: string[] = [];
  const cursor = new Date(today.getFullYear(), today.getMonth(), 1);

  while (cursor <= maxDate) {
    const year = cursor.getFullYear();
    const month = `${cursor.getMonth() + 1}`.padStart(2, "0");
    months.push(`${year}-${month}`);
    cursor.setMonth(cursor.getMonth() + 1);
  }

  return months;
}

function formatMonthLabel(month: string, copy: typeof uiText.ja) {
  const [year, monthIndex] = month.split("-").map(Number);
  return new Intl.DateTimeFormat(localeToDateFormat(copy), {
    year: "numeric",
    month: "long",
  }).format(new Date(year, monthIndex - 1, 1));
}

function buildMonthDates(month: string) {
  const [year, monthIndex] = month.split("-").map(Number);
  const lastDay = new Date(year, monthIndex, 0).getDate();
  return Array.from({ length: lastDay }, (_, index) => {
    const day = `${index + 1}`.padStart(2, "0");
    return `${year}-${`${monthIndex}`.padStart(2, "0")}-${day}`;
  });
}

function weekdayLabel(date: string, copy: typeof uiText.ja) {
  const formatter = new Intl.DateTimeFormat(localeToDateFormat(copy), { weekday: "short" });
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
  copy,
  engagement,
  postedPosts
}: {
  analytics: { views: number; likes: number; replies: number; reposts: number; quotes: number; shares: number };
  copy: typeof uiText.ja;
  engagement: number;
  postedPosts: ScheduledPost[];
}) {
  const analyzedPosts = postedPosts.filter((post) => post.metrics);
  const statItems = [
    { label: copy.analytics.views, value: analytics.views },
    { label: copy.analytics.likes, value: analytics.likes },
    { label: copy.analytics.replies, value: analytics.replies },
    { label: copy.analytics.reposts, value: analytics.reposts },
    { label: copy.analytics.quotes, value: analytics.quotes },
    { label: copy.analytics.shares, value: analytics.shares }
  ];

  return (
    <div className="analytics-layout">
      <section className="metric-strip">
        <div className="metric">
          <span>{copy.analytics.analyzedPosts}</span>
          <strong>{analyzedPosts.length.toLocaleString()}</strong>
        </div>
        {statItems.map((item) => (
          <div className="metric" key={item.label}>
            <span>{item.label}</span>
            <strong>{item.value.toLocaleString()}</strong>
          </div>
        ))}
        <div className="metric strong">
          <span>{copy.analytics.engagement}</span>
          <strong>{engagement.toLocaleString()}</strong>
        </div>
      </section>
      <section className="panel">
        <div className="section-heading">
          <div>
            <p className="eyebrow">{copy.analytics.eyebrow}</p>
            <h2>{copy.analytics.title}</h2>
          </div>
          <span className="pill muted">{copy.analytics.cumulative}</span>
        </div>
        {analyzedPosts.length === 0 ? (
          <p className="muted-text">{copy.analytics.noData}</p>
        ) : (
          <div className="post-list">
            {analyzedPosts.map((post) => (
            <article className="post-row" key={post.id}>
              <div className="status-dot success">
                <BarChart3 size={17} />
              </div>
              <div className="post-main">
                <div className="post-meta">
                  <span>{post.date}</span>
                  <span>{copy.analytics.latestStage}: {post.analyticsStage || "-"}</span>
                  {post.analyticsFetchedAt ? <span>{formatUnixDate(post.analyticsFetchedAt, copy)}</span> : null}
                </div>
                <p>{post.content}</p>
              </div>
              <strong>{post.metrics ? post.metrics.likes + post.metrics.replies + post.metrics.reposts + post.metrics.quotes + post.metrics.shares : 0}</strong>
            </article>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}

function getTodayDate() {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  return today.toLocaleDateString("sv-SE");
}

function getMaxReservableDate() {
  const maxDate = new Date();
  maxDate.setHours(0, 0, 0, 0);
  maxDate.setDate(maxDate.getDate() + 30);
  return maxDate.toLocaleDateString("sv-SE");
}

function SettingsView({
  locale,
  needsReconnect,
  onDeleteAccount,
  onOpenBillingPortal,
  onOpenLegalDocument,
  onReconnect,
  onSaveSettings,
  onStartCheckout,
  onStatusChange,
  setLocale,
  setSettingsTimezone,
  settingsTimezone,
  canStartCheckout,
  copy,
  subscriptionStatus,
  trialStartedAt,
  trialEnd,
  userStatus
}: {
  locale: string;
  needsReconnect: boolean;
  onDeleteAccount: () => Promise<void>;
  onOpenBillingPortal: () => Promise<void>;
  onOpenLegalDocument: (document: LegalDocument) => void;
  onReconnect: () => void;
  onSaveSettings: (nextLocale?: string, nextTimezone?: string) => Promise<void>;
  onStartCheckout: () => Promise<void>;
  onStatusChange: (nextStatus: "active" | "paused") => Promise<void>;
  setLocale: (locale: string) => void;
  setSettingsTimezone: (timezone: string) => void;
  settingsTimezone: string;
  canStartCheckout: boolean;
  copy: typeof uiText.ja;
  subscriptionStatus: SubscriptionStatus;
  trialStartedAt: number | null;
  trialEnd: number | null;
  userStatus: UserStatus;
}) {
  const canManagePaidAccount = subscriptionStatus === "active";

  return (
    <div className="settings-layout">
      <section className="panel">
        <div className="section-heading">
          <div>
            <p className="eyebrow">{copy.settings.eyebrow}</p>
            <h2>{copy.settings.title}</h2>
          </div>
        </div>
        <div className="settings-list">
          <label className="setting-control">
            <Globe2 size={18} />
            <span>{copy.settings.locale}</span>
            <select
              value={locale}
              onChange={(event) => {
                const nextLocale = event.target.value;
                setLocale(nextLocale);
                void onSaveSettings(nextLocale, settingsTimezone);
              }}
            >
              {localeLabels.map((item) => (
                <option key={item.code} value={item.code}>
                  {item.flag} {item.label}
                </option>
              ))}
            </select>
          </label>
          <label className="setting-control">
            <Clock3 size={18} />
            <span>{copy.settings.timezone}</span>
            <select
              value={settingsTimezone}
              onChange={(event) => {
                const nextTimezone = event.target.value;
                setSettingsTimezone(nextTimezone);
                void onSaveSettings(locale, nextTimezone);
              }}
            >
              <option value="Asia/Tokyo">Asia/Tokyo</option>
              <option value="America/Los_Angeles">America/Los_Angeles</option>
              <option value="Europe/London">Europe/London</option>
              <option value="Asia/Manila">Asia/Manila</option>
              <option value="Asia/Ho_Chi_Minh">Asia/Ho_Chi_Minh</option>
            </select>
          </label>
          <SettingRow
            action={
              needsReconnect ? (
                <button className="button secondary compact" onClick={onReconnect}>
                  <RefreshCcw size={16} />
                  {copy.reconnect.shortButton}
                </button>
              ) : undefined
            }
            icon={RefreshCcw}
            label={copy.settings.threads}
            value={needsReconnect ? copy.reconnect.needed : copy.reconnect.enabled}
          />
          <SettingRow icon={PauseCircle} label={copy.settings.userStatus} value={userStatus === "paused" ? copy.paused.paused : copy.paused.active} />
          <SettingRow icon={CreditCard} label={copy.settings.billingStatus} value={billingStatusLabel(subscriptionStatus, copy)} />
          <SettingRow icon={Clock3} label={copy.settings.trialPeriod} value={trialPeriodLabel(trialStartedAt, trialEnd, copy)} />
        </div>
        <div className="button-row">
          {canStartCheckout && (
            <button className="button primary" onClick={() => void onStartCheckout()}>
              <CreditCard size={16} />
              {copy.billing.checkout}
            </button>
          )}
          {canManagePaidAccount && (
            <>
              <button className="button primary" onClick={() => void onOpenBillingPortal()}>
                <CreditCard size={16} />
                {copy.billing.portal}
              </button>
              <button
                className="button secondary"
                onClick={() => void onStatusChange(userStatus === "paused" ? "active" : "paused")}
              >
                <PauseCircle size={16} />
                {userStatus === "paused" ? copy.paused.resume : copy.paused.pause}
              </button>
              <button className="button danger" onClick={() => void onDeleteAccount()}>
                <Trash2 size={16} />
                {copy.settings.delete}
              </button>
            </>
          )}
        </div>
        {canManagePaidAccount && (
          <div className="account-action-notes">
            <p>{copy.settings.pauseNote}</p>
            <p>{copy.settings.deleteNote}</p>
          </div>
        )}
      </section>
      <section className="panel">
        <div className="section-heading">
          <div>
            <p className="eyebrow">{copy.settings.legalEyebrow}</p>
            <h2>{copy.settings.legalTitle}</h2>
          </div>
        </div>
        <div className="legal-links">
          <button type="button" onClick={() => onOpenLegalDocument("commerce")}>
            {copy.legal.commerce}
          </button>
          <button type="button" onClick={() => onOpenLegalDocument("terms")}>
            {copy.legal.terms}
          </button>
          <button type="button" onClick={() => onOpenLegalDocument("privacy")}>
            {copy.legal.privacy}
          </button>
        </div>
      </section>
    </div>
  );
}

function LegalDocumentDialog({
  copy,
  document,
  onClose,
}: {
  copy: typeof uiText.ja;
  document: LegalDocument;
  onClose: () => void;
}) {
  return (
    <div className="modal-backdrop" role="presentation">
      <section className="modal-panel legal-modal" role="dialog" aria-modal="true" aria-labelledby="legal-title">
        <h2 id="legal-title">{copy.legal[document]}</h2>
        <div className="legal-document-text">
          {legalDocumentBody(document)}
        </div>
        <div className="button-row end">
          <button className="button primary" onClick={onClose}>
            {copy.settings.close}
          </button>
        </div>
      </section>
    </div>
  );
}

function DeveloperView({
  dashboard,
  error,
  isLoading,
  onRefresh,
  onResolveReview,
  copy
}: {
  dashboard: DeveloperDashboard | null;
  error: string;
  isLoading: boolean;
  onRefresh: () => Promise<void>;
  onResolveReview: (appUserId: string) => Promise<void>;
  copy: typeof uiText.ja;
}) {
  const metrics = dashboard?.metrics;
  const metricItems = [
    { label: copy.developer.totalUsers, value: metrics?.total_users ?? 0 },
    { label: copy.developer.trialUsers, value: metrics?.trial_users ?? 0 },
    { label: copy.developer.subscribedUsers, value: metrics?.subscribed_users ?? 0 },
    { label: copy.developer.cvr, value: `${metrics?.cvr ?? 0}%` },
    { label: copy.developer.reviewCount, value: metrics?.admin_review_items ?? 0 },
    { label: copy.developer.subscriptionsTotal, value: metrics?.subscriptions_total ?? 0 },
  ];

  return (
    <div className="settings-layout">
      <section className="metric-strip">
        {metricItems.map((item) => (
          <div className="metric" key={item.label}>
            <span>{item.label}</span>
            <strong>{item.value}</strong>
          </div>
        ))}
      </section>
      <section className="panel">
        <div className="section-heading">
          <div>
            <p className="eyebrow">{copy.developer.reviewCount}</p>
            <h2>{copy.developer.adminReview}</h2>
          </div>
          <button className="button secondary compact" onClick={() => void onRefresh()}>
            <RefreshCcw size={16} />
            {isLoading ? copy.developer.loading : copy.reconnect.shortButton}
          </button>
        </div>
        {error && <p className="muted-text">{error}</p>}
        {isLoading && !dashboard && <p className="muted-text">{copy.developer.loading}</p>}
        {!isLoading && !error && dashboard?.admin_review_items.length === 0 && (
          <p className="muted-text">{copy.developer.noReviewItems}</p>
        )}
        <div className="post-list">
          {(dashboard?.admin_review_items ?? []).map((item) => (
            <article className="post-row" key={`${item.app_user_id}-${item.stripe_subscription_id}`}>
              <div className="status-dot danger">
                <AlertTriangle size={17} />
              </div>
              <div className="post-main">
                <div className="post-meta">
                  <span>{copy.developer.user}: {item.display_name || item.threads_user_id || item.app_user_id}</span>
                  <span>{copy.developer.failedAt}: {formatUnixDate(item.stripe_cancel_failed_at || item.updated_at, copy)}</span>
                </div>
                <p>{copy.developer.reason}: {item.reason || "-"}</p>
                <p>{copy.developer.stripeSubscription}: {item.stripe_subscription_id || "-"}</p>
                {item.stripe_cancel_error && <p>{copy.developer.error}: {item.stripe_cancel_error}</p>}
              </div>
              <div className="row-actions">
                <strong>{item.status}</strong>
                <button className="button secondary compact" onClick={() => void onResolveReview(item.app_user_id)}>
                  <CheckCircle2 size={16} />
                  {copy.developer.resolve}
                </button>
              </div>
            </article>
          ))}
        </div>
      </section>
    </div>
  );
}

function legalDocumentBody(document: LegalDocument) {
  const headings = Object.values(legalDocuments).map((item) => item.heading);
  const heading = legalDocuments[document].heading;
  const start = legalPoliciesText.indexOf(heading);
  if (start < 0) return legalPoliciesText;

  const nextHeadingStart = headings
    .filter((item) => item !== heading)
    .map((item) => legalPoliciesText.indexOf(item, start + heading.length))
    .filter((index) => index > start)
    .sort((a, b) => a - b)[0];

  const body = legalPoliciesText.slice(start, nextHeadingStart ?? undefined);
  return body.replace(/^##\s*/, "").trim();
}

function SettingRow({
  action,
  icon: Icon,
  label,
  value
}: {
  action?: ReactNode;
  icon: typeof Globe2;
  label: string;
  value: string;
}) {
  return (
    <div className="setting-row">
      <Icon size={18} />
      <span>{label}</span>
      <div className="setting-row-value">
        <strong>{value}</strong>
        {action}
      </div>
    </div>
  );
}

function ConfirmDialog({
  copy,
  draft,
  editingId,
  isSubmitting,
  onCancel,
  onConfirm
}: {
  copy: typeof uiText.ja;
  draft: { date: string; time: string; timezone: string; content: string };
  editingId: string | null;
  isSubmitting: boolean;
  onCancel: () => void;
  onConfirm: () => Promise<void>;
}) {
  return (
    <div className="modal-backdrop" role="presentation">
      <section className="modal-panel" role="dialog" aria-modal="true" aria-labelledby="confirm-title">
        <h2 id="confirm-title">{editingId ? copy.settings.confirmEditTitle : copy.settings.confirmTitle}</h2>
        <dl className="confirm-list">
          <div>
            <dt>{copy.settings.dateTime}</dt>
            <dd>
              {draft.date} {draft.time}
            </dd>
          </div>
          <div>
            <dt>{copy.settings.timezone}</dt>
            <dd>{draft.timezone}</dd>
          </div>
          <div>
            <dt>{copy.settings.body}</dt>
            <dd>{draft.content}</dd>
          </div>
        </dl>
        <div className="button-row end">
          <button className="button secondary" disabled={isSubmitting} onClick={onCancel}>
            {copy.settings.back}
          </button>
          <button className="button primary" disabled={isSubmitting} onClick={() => void onConfirm()}>
            {isSubmitting ? copy.settings.sending : editingId ? copy.settings.update : copy.settings.reserve}
          </button>
        </div>
      </section>
    </div>
  );
}

export default App;
