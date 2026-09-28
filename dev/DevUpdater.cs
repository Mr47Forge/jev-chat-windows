using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.Diagnostics;
using System.Drawing;
using System.IO;
using System.IO.Compression;
using System.Net;
using System.Windows.Forms;

namespace JevChatDevUpdater
{
    internal sealed class UpdaterForm : Form
    {
        private static readonly string[] RepoZips = new string[]
        {
            "https://codeload.github.com/Mr47Forge/jev-chat-windows/zip/refs/heads/dev-external-source",
            "https://github.com/Mr47Forge/jev-chat-windows/archive/refs/heads/dev-external-source.zip"
        };

        private readonly Label statusLabel;
        private readonly TextBox detailBox;
        private readonly ProgressBar progress;
        private readonly Button retryButton;
        private readonly Button closeButton;
        private readonly BackgroundWorker worker;
        private readonly string root;

        private sealed class TimeoutWebClient : WebClient
        {
            public int TimeoutMs { get; set; }
            public TimeoutWebClient(int timeoutMs) { TimeoutMs = timeoutMs; }

            protected override WebRequest GetWebRequest(Uri address)
            {
                WebRequest request = base.GetWebRequest(address);
                request.Timeout = TimeoutMs;
                HttpWebRequest http = request as HttpWebRequest;
                if (http != null)
                {
                    http.ReadWriteTimeout = TimeoutMs;
                    http.AutomaticDecompression = DecompressionMethods.GZip | DecompressionMethods.Deflate;
                }
                return request;
            }
        }

        private sealed class SyncPlan
        {
            public string Generation = "";
            public readonly List<string> Dirs = new List<string>();
            public readonly List<string> Files = new List<string>();
            public readonly List<string> Required = new List<string>();
        }

        public UpdaterForm()
        {
            root = AppDomain.CurrentDomain.BaseDirectory;
            Text = "Jev 开发源码更新";
            StartPosition = FormStartPosition.CenterScreen;
            FormBorderStyle = FormBorderStyle.FixedDialog;
            MaximizeBox = false;
            MinimizeBox = true;
            Width = 590;
            Height = 370;
            Font = new Font("Microsoft YaHei UI", 9F);

            Label titleLabel = new Label();
            titleLabel.Text = "JevChat-Windows 开发源码同步 V2";
            titleLabel.Font = new Font(Font.FontFamily, 14F, FontStyle.Bold);
            titleLabel.AutoSize = true;
            titleLabel.Left = 24;
            titleLabel.Top = 22;
            Controls.Add(titleLabel);

            statusLabel = new Label();
            statusLabel.Text = "准备更新…";
            statusLabel.Left = 24;
            statusLabel.Top = 62;
            statusLabel.Width = 535;
            statusLabel.Height = 26;
            Controls.Add(statusLabel);

            progress = new ProgressBar();
            progress.Left = 24;
            progress.Top = 92;
            progress.Width = 535;
            progress.Height = 20;
            progress.Style = ProgressBarStyle.Marquee;
            Controls.Add(progress);

            detailBox = new TextBox();
            detailBox.Left = 24;
            detailBox.Top = 126;
            detailBox.Width = 535;
            detailBox.Height = 145;
            detailBox.Multiline = true;
            detailBox.ReadOnly = true;
            detailBox.ScrollBars = ScrollBars.Vertical;
            detailBox.Text =
                "V2 不再写死 app/core。它读取仓库里的 dev/runtime-sync.txt，按当前项目结构同步。\r\n" +
                "当前会同步 main.py / app / core / vendor；不会覆盖用户配置、聊天资料和长期记忆数据库。";
            Controls.Add(detailBox);

            retryButton = new Button();
            retryButton.Text = "重新尝试";
            retryButton.Width = 100;
            retryButton.Height = 32;
            retryButton.Left = 353;
            retryButton.Top = 289;
            retryButton.Enabled = false;
            retryButton.Click += delegate { StartUpdate(); };
            Controls.Add(retryButton);

            closeButton = new Button();
            closeButton.Text = "关闭";
            closeButton.Width = 100;
            closeButton.Height = 32;
            closeButton.Left = 459;
            closeButton.Top = 289;
            closeButton.Click += delegate { Close(); };
            Controls.Add(closeButton);

            worker = new BackgroundWorker();
            worker.WorkerReportsProgress = true;
            worker.DoWork += WorkerDoWork;
            worker.ProgressChanged += WorkerProgressChanged;
            worker.RunWorkerCompleted += WorkerCompleted;
            Shown += delegate { BeginInvoke((MethodInvoker)StartUpdate); };
        }

        private void StartUpdate()
        {
            if (worker.IsBusy) return;

            if (Process.GetProcessesByName("JevChat-Dev").Length > 0)
            {
                statusLabel.Text = "请先关闭 JevChat-Dev.exe";
                detailBox.Text = "检测到 JevChat-Dev 仍在运行。\r\n关闭后再点击“重新尝试”。";
                progress.Style = ProgressBarStyle.Blocks;
                progress.Value = 0;
                retryButton.Enabled = true;
                return;
            }

            retryButton.Enabled = false;
            progress.Style = ProgressBarStyle.Marquee;
            statusLabel.Text = "正在开始更新…";
            detailBox.Text = "读取 V2 同步清单；源码和 vendor 会一起同步，用户数据不会动。";
            worker.RunWorkerAsync();
        }

        private void WorkerDoWork(object sender, DoWorkEventArgs e)
        {
            string temp = Path.Combine(Path.GetTempPath(), "jev-chat-dev-update-" + Guid.NewGuid().ToString("N"));
            string zip = Path.Combine(temp, "src.zip");
            string extract = Path.Combine(temp, "src");
            string stage = Path.Combine(temp, "stage");
            string backup = Path.Combine(temp, "backup");
            var existed = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
            SyncPlan plan = null;

            try
            {
                Directory.CreateDirectory(temp);
                ServicePointManager.SecurityProtocol = (SecurityProtocolType)3072;

                IWebProxy systemProxy = WebRequest.DefaultWebProxy;
                Report("正在下载 dev-external-source…");
                Exception last = null;
                bool downloaded = false;
                for (int i = 0; i < RepoZips.Length; i++)
                {
                    try
                    {
                        if (File.Exists(zip)) File.Delete(zip);
                        using (TimeoutWebClient client = new TimeoutWebClient(20000))
                        {
                            client.Proxy = systemProxy;
                            if (client.Proxy != null)
                                client.Proxy.Credentials = CredentialCache.DefaultCredentials;
                            client.Headers[HttpRequestHeader.UserAgent] = "JevChat-Dev-Updater-V2";
                            client.DownloadFile(RepoZips[i], zip);
                        }
                        if (!File.Exists(zip) || new FileInfo(zip).Length < 1024)
                            throw new InvalidOperationException("下载包为空或无效");
                        downloaded = true;
                        break;
                    }
                    catch (Exception ex) { last = ex; }
                }
                if (!downloaded)
                    throw new InvalidOperationException("GitHub 下载失败：" + (last == null ? "未知错误" : last.Message));

                Report("正在解压并读取同步清单…");
                Directory.CreateDirectory(extract);
                ZipFile.ExtractToDirectory(zip, extract);
                string[] roots = Directory.GetDirectories(extract);
                if (roots.Length == 0)
                    throw new InvalidOperationException("下载包结构异常");
                string source = roots[0];

                string manifest = Path.Combine(source, "dev", "runtime-sync.txt");
                if (!File.Exists(manifest))
                    throw new InvalidOperationException("新源码缺少 dev/runtime-sync.txt，拒绝按旧结构覆盖");
                plan = LoadPlan(manifest);

                string localGeneration = ReadTrimmed(Path.Combine(root, "runtime-generation.txt"));
                if (String.IsNullOrEmpty(localGeneration))
                    throw new InvalidOperationException("当前开发运行时太旧，缺少 runtime-generation.txt。请重新下载一次完整 JevChat-Windows-Dev。");
                if (!String.Equals(localGeneration, plan.Generation, StringComparison.Ordinal))
                    throw new InvalidOperationException(
                        "运行时代际已变化（本地 " + localGeneration + "，源码 " + plan.Generation + "）。\r\n" +
                        "这次不能只同步源码，请重新下载完整 JevChat-Windows-Dev。"
                    );

                string localRequirements = Path.Combine(root, "requirements.txt");
                string sourceRequirements = Path.Combine(source, "requirements.txt");
                if (File.Exists(localRequirements) && File.Exists(sourceRequirements) &&
                    !FilesEqual(localRequirements, sourceRequirements))
                {
                    throw new InvalidOperationException("requirements.txt 已变化，冻结运行时可能缺依赖。请重新下载完整开发环境。");
                }

                Directory.CreateDirectory(stage);
                foreach (string rel in plan.Dirs)
                {
                    string src = SafeCombine(source, rel);
                    string dst = SafeCombine(stage, rel);
                    if (!Directory.Exists(src))
                        throw new InvalidOperationException("同步清单目录不存在：" + rel);
                    CopyDirectory(src, dst);
                }
                foreach (string rel in plan.Files)
                {
                    string src = SafeCombine(source, rel);
                    string dst = SafeCombine(stage, rel);
                    if (!File.Exists(src))
                        throw new InvalidOperationException("同步清单文件不存在：" + rel);
                    Directory.CreateDirectory(Path.GetDirectoryName(dst));
                    File.Copy(src, dst, true);
                }
                foreach (string rel in plan.Required)
                {
                    string path = SafeCombine(stage, rel);
                    if (!File.Exists(path) && !Directory.Exists(path))
                        throw new InvalidOperationException("新版结构校验失败，缺少：" + rel);
                }

                Report("正在备份当前业务源码…");
                Directory.CreateDirectory(backup);
                foreach (string rel in AllTargets(plan))
                {
                    string current = SafeCombine(root, rel);
                    string save = SafeCombine(backup, rel);
                    if (Directory.Exists(current))
                    {
                        existed.Add(rel);
                        CopyDirectory(current, save);
                    }
                    else if (File.Exists(current))
                    {
                        existed.Add(rel);
                        Directory.CreateDirectory(Path.GetDirectoryName(save));
                        File.Copy(current, save, true);
                    }
                }

                try
                {
                    Report("正在按 V2 清单替换源码…");
                    DeleteDirectoryIfExists(Path.Combine(root, "__pycache__"));
                    foreach (string rel in plan.Dirs)
                        ReplaceDirectory(SafeCombine(stage, rel), SafeCombine(root, rel));
                    foreach (string rel in plan.Files)
                        ReplaceFile(SafeCombine(stage, rel), SafeCombine(root, rel));

                    foreach (string rel in plan.Required)
                    {
                        string path = SafeCombine(root, rel);
                        if (!File.Exists(path) && !Directory.Exists(path))
                            throw new InvalidOperationException("更新后校验失败，缺少：" + rel);
                    }
                }
                catch
                {
                    Report("更新失败，正在回滚…");
                    Restore(plan, backup, existed);
                    throw;
                }

                e.Result = null;
            }
            catch (Exception ex) { e.Result = ex; }
            finally
            {
                try { if (Directory.Exists(temp)) Directory.Delete(temp, true); } catch { }
            }
        }

        private static SyncPlan LoadPlan(string manifest)
        {
            var plan = new SyncPlan();
            foreach (string raw in File.ReadAllLines(manifest))
            {
                string line = raw.Trim();
                if (line.Length == 0 || line.StartsWith("#") || line == "JEV_RUNTIME_SYNC_V2")
                    continue;
                int pos = line.IndexOf('=');
                if (pos <= 0) continue;
                string key = line.Substring(0, pos).Trim();
                string value = line.Substring(pos + 1).Trim().Replace('/', Path.DirectorySeparatorChar);
                ValidateRelative(value);
                if (key == "generation") plan.Generation = value;
                else if (key == "dir") plan.Dirs.Add(value);
                else if (key == "file") plan.Files.Add(value);
                else if (key == "required") plan.Required.Add(value);
            }
            if (String.IsNullOrEmpty(plan.Generation))
                throw new InvalidOperationException("同步清单缺少 generation");
            if (plan.Dirs.Count == 0 && plan.Files.Count == 0)
                throw new InvalidOperationException("同步清单为空");
            return plan;
        }

        private static IEnumerable<string> AllTargets(SyncPlan plan)
        {
            foreach (string x in plan.Dirs) yield return x;
            foreach (string x in plan.Files) yield return x;
        }

        private static void ValidateRelative(string rel)
        {
            if (String.IsNullOrWhiteSpace(rel) || Path.IsPathRooted(rel) ||
                rel == "." || rel == ".." || rel.StartsWith(".." + Path.DirectorySeparatorChar) ||
                rel.Contains(Path.DirectorySeparatorChar + ".." + Path.DirectorySeparatorChar))
                throw new InvalidOperationException("非法同步路径：" + rel);
        }

        private static string SafeCombine(string baseDir, string rel)
        {
            ValidateRelative(rel);
            string fullBase = Path.GetFullPath(baseDir).TrimEnd(Path.DirectorySeparatorChar) + Path.DirectorySeparatorChar;
            string full = Path.GetFullPath(Path.Combine(baseDir, rel));
            if (!full.StartsWith(fullBase, StringComparison.OrdinalIgnoreCase))
                throw new InvalidOperationException("同步路径越界：" + rel);
            return full;
        }

        private void Restore(SyncPlan plan, string backup, HashSet<string> existed)
        {
            foreach (string rel in AllTargets(plan))
            {
                string target = SafeCombine(root, rel);
                if (Directory.Exists(target)) DeleteDirectoryIfExists(target);
                else if (File.Exists(target)) File.Delete(target);

                if (!existed.Contains(rel)) continue;
                string saved = SafeCombine(backup, rel);
                if (Directory.Exists(saved)) CopyDirectory(saved, target);
                else if (File.Exists(saved))
                {
                    Directory.CreateDirectory(Path.GetDirectoryName(target));
                    File.Copy(saved, target, true);
                }
            }
        }

        private static string ReadTrimmed(string path)
        {
            return File.Exists(path) ? File.ReadAllText(path).Trim() : "";
        }

        private static bool FilesEqual(string a, string b)
        {
            byte[] aa = File.ReadAllBytes(a);
            byte[] bb = File.ReadAllBytes(b);
            if (aa.Length != bb.Length) return false;
            for (int i = 0; i < aa.Length; i++) if (aa[i] != bb[i]) return false;
            return true;
        }

        private static void ReplaceFile(string source, string destination)
        {
            Directory.CreateDirectory(Path.GetDirectoryName(destination));
            if (File.Exists(destination)) File.SetAttributes(destination, FileAttributes.Normal);
            File.Copy(source, destination, true);
        }

        private static void ReplaceDirectory(string source, string destination)
        {
            if (Directory.Exists(destination)) DeleteDirectoryIfExists(destination);
            CopyDirectory(source, destination);
        }

        private static void DeleteDirectoryIfExists(string directory)
        {
            if (!Directory.Exists(directory)) return;
            ClearReadOnly(directory);
            Directory.Delete(directory, true);
        }

        private static void CopyDirectory(string source, string destination)
        {
            Directory.CreateDirectory(destination);
            foreach (string file in Directory.GetFiles(source))
                File.Copy(file, Path.Combine(destination, Path.GetFileName(file)), true);
            foreach (string dir in Directory.GetDirectories(source))
                CopyDirectory(dir, Path.Combine(destination, Path.GetFileName(dir)));
        }

        private static void ClearReadOnly(string directory)
        {
            foreach (string file in Directory.GetFiles(directory, "*", SearchOption.AllDirectories))
            {
                try
                {
                    FileAttributes attrs = File.GetAttributes(file);
                    if ((attrs & FileAttributes.ReadOnly) != 0)
                        File.SetAttributes(file, attrs & ~FileAttributes.ReadOnly);
                }
                catch { }
            }
        }

        private void Report(string text) { worker.ReportProgress(0, text); }

        private void WorkerProgressChanged(object sender, ProgressChangedEventArgs e)
        {
            string text = e.UserState as string;
            if (!String.IsNullOrEmpty(text))
            {
                statusLabel.Text = text;
                detailBox.AppendText("\r\n" + text);
            }
        }

        private void WorkerCompleted(object sender, RunWorkerCompletedEventArgs e)
        {
            Exception ex = e.Result as Exception;
            progress.Style = ProgressBarStyle.Blocks;
            if (ex == null)
            {
                progress.Value = 100;
                statusLabel.Text = "更新成功";
                detailBox.AppendText("\r\n\r\nV2 同步完成，可以重新打开 JevChat-Dev.exe。");
                retryButton.Enabled = true;
                retryButton.Text = "再次更新";
                MessageBox.Show(this, "业务源码和 vendor 已同步完成。", "Jev", MessageBoxButtons.OK, MessageBoxIcon.Information);
            }
            else
            {
                progress.Value = 0;
                statusLabel.Text = "更新失败";
                detailBox.AppendText("\r\n\r\n失败原因：\r\n" + ex.Message);
                retryButton.Enabled = true;
                MessageBox.Show(this, ex.Message, "更新失败", MessageBoxButtons.OK, MessageBoxIcon.Error);
            }
        }
    }

    internal static class Program
    {
        [STAThread]
        private static void Main()
        {
            Application.EnableVisualStyles();
            Application.SetCompatibleTextRenderingDefault(false);
            Application.Run(new UpdaterForm());
        }
    }
}
