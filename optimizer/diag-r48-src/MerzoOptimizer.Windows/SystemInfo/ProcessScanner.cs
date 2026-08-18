using System.Diagnostics;
using MerzoOptimizer.Core.Models;

namespace MerzoOptimizer.Windows.SystemInfo;

internal static class ProcessScanner
{
    public static ProcessScanResult Scan(int topCount = 50)
    {
        var items = new List<ProcessSnapshot>();
        var processes = Process.GetProcesses();

        foreach (var process in processes)
        {
            try
            {
                var sessionId = process.SessionId;
                items.Add(new ProcessSnapshot(
                    process.ProcessName,
                    process.Id,
                    Math.Max(0, process.WorkingSet64),
                    sessionId,
                    sessionId == 0));
            }
            catch
            {
                // Some protected/system processes cannot be fully queried.
            }
            finally
            {
                process.Dispose();
            }
        }

        var ordered = items
            .OrderByDescending(static item => item.WorkingSetBytes)
            .ThenBy(static item => item.Name, StringComparer.OrdinalIgnoreCase)
            .Take(Math.Max(1, topCount))
            .ToArray();

        return new ProcessScanResult(
            items.Count,
            items.Count(static item => item.IsSystemSession),
            items.Count(static item => !item.IsSystemSession),
            ordered);
    }
}

internal sealed record ProcessScanResult(
    int TotalCount,
    int SystemCount,
    int UserCount,
    IReadOnlyList<ProcessSnapshot> TopProcesses);
