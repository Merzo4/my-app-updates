using MerzoOptimizer.Core.Models;

namespace MerzoOptimizer.Windows.Storage;

internal static class StorageScanner
{
    public static IReadOnlyList<StorageSnapshot> Scan()
    {
        var result = new List<StorageSnapshot>();

        foreach (var drive in DriveInfo.GetDrives())
        {
            try
            {
                if (!drive.IsReady)
                    continue;

                result.Add(new StorageSnapshot(
                    drive.Name,
                    drive.DriveType.ToString(),
                    drive.DriveFormat,
                    drive.TotalSize,
                    drive.AvailableFreeSpace));
            }
            catch
            {
                // Some removable/network drives can disappear during enumeration.
            }
        }

        return result;
    }
}
