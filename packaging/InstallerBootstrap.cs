using System;
using System.Diagnostics;
using System.IO;
using System.IO.Compression;
using System.Reflection;
using System.Text;

internal static class InstallerBootstrap
{
    private static int Main(string[] args)
    {
        try
        {
            using (var stream = new FileStream(Assembly.GetExecutingAssembly().Location, FileMode.Open, FileAccess.Read, FileShare.Read))
            using (var zip = new ZipArchive(stream, ZipArchiveMode.Read))
            {
                if (args.Length > 0 && args[0] == "--selftest")
                {
                    Console.WriteLine("ZIP_OK " + zip.Entries.Count + " entries");
                    return 0;
                }

                string destination = Path.Combine(
                    Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
                    "LocalStudio");
                Directory.CreateDirectory(destination);
                string destinationPrefix = Path.GetFullPath(destination).TrimEnd(Path.DirectorySeparatorChar) + Path.DirectorySeparatorChar;
                Console.WriteLine("Installing Local Studio to " + destination);
                int count = 0;
                foreach (ZipArchiveEntry entry in zip.Entries)
                {
                    string relative = entry.FullName.Replace('/', Path.DirectorySeparatorChar);
                    string target = Path.GetFullPath(Path.Combine(destination, relative));
                    if (!target.StartsWith(destinationPrefix, StringComparison.OrdinalIgnoreCase))
                        throw new InvalidDataException("Unsafe archive path: " + entry.FullName);
                    if (entry.FullName.EndsWith("/"))
                    {
                        Directory.CreateDirectory(target);
                        continue;
                    }
                    Directory.CreateDirectory(Path.GetDirectoryName(target));
                    using (var input = entry.Open())
                    using (var output = new FileStream(target, FileMode.Create, FileAccess.Write, FileShare.None))
                        input.CopyTo(output);
                    count++;
                    if (count % 1000 == 0)
                        Console.WriteLine("Installed " + count + " files...");
                }

                string config = Path.Combine(destination, ".venv", "pyvenv.cfg");
                File.WriteAllText(config,
                    "home = " + Path.Combine(destination, "runtime") + Environment.NewLine +
                    "include-system-site-packages = false" + Environment.NewLine +
                    "version_info = 3.11" + Environment.NewLine,
                    new UTF8Encoding(false));
                string launcher = Path.Combine(destination, "RUN-LOCAL-STUDIO.cmd");
                CreateDesktopShortcut(launcher, destination);
                Console.WriteLine("Installed " + count + " files. Starting Local Studio...");
                Process.Start(new ProcessStartInfo(launcher) {
                    UseShellExecute = true,
                    WorkingDirectory = destination
                });
                return 0;
            }
        }
        catch (Exception error)
        {
            Console.Error.WriteLine("Installation failed: " + error);
            Console.WriteLine("Press Enter to close.");
            Console.ReadLine();
            return 1;
        }
    }

    private static void CreateDesktopShortcut(string launcher, string destination)
    {
        Type shellType = Type.GetTypeFromProgID("WScript.Shell");
        if (shellType == null)
            throw new InvalidOperationException("Windows shortcut service unavailable");
        object shell = Activator.CreateInstance(shellType);
        string desktop = Environment.GetFolderPath(Environment.SpecialFolder.DesktopDirectory);
        string shortcutPath = Path.Combine(desktop, "Local Studio.lnk");
        object shortcut = shellType.InvokeMember("CreateShortcut", BindingFlags.InvokeMethod,
            null, shell, new object[] { shortcutPath });
        Type shortcutType = shortcut.GetType();
        shortcutType.InvokeMember("TargetPath", BindingFlags.SetProperty,
            null, shortcut, new object[] { launcher });
        shortcutType.InvokeMember("WorkingDirectory", BindingFlags.SetProperty,
            null, shortcut, new object[] { destination });
        shortcutType.InvokeMember("IconLocation", BindingFlags.SetProperty,
            null, shortcut, new object[] { Path.Combine(destination, "src", "icon.ico") });
        shortcutType.InvokeMember("Save", BindingFlags.InvokeMethod,
            null, shortcut, new object[0]);
    }
}
