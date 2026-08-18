using System.Runtime.InteropServices;
using System.Text;
using MerzoOptimizer.Core.Power;

namespace MerzoOptimizer.Windows.Power;

internal static class PowerPlanReader
{
    private const uint ErrorSuccess = 0;
    private const uint ErrorNoMoreItems = 259;
    private const uint AccessScheme = 16;

    public static Task<string> ReadActivePlanAsync(CancellationToken cancellationToken)
    {
        cancellationToken.ThrowIfCancellationRequested();
        return Task.FromResult(ReadActivePlanNative());
    }

    public static IReadOnlyList<PowerSchemeInfo> ReadAllSchemes()
    {
        var result = new List<PowerSchemeInfo>();
        var activeGuid = ReadActiveGuid();

        for (uint index = 0; index < 128; index++)
        {
            uint bufferSize = 16;
            var buffer = new byte[bufferSize];
            var status = PowerEnumerate(
                IntPtr.Zero,
                IntPtr.Zero,
                IntPtr.Zero,
                AccessScheme,
                index,
                buffer,
                ref bufferSize);

            if (status == ErrorNoMoreItems)
                break;
            if (status != ErrorSuccess || bufferSize < 16)
                continue;

            var guid = new Guid(buffer.AsSpan(0, 16));
            var name = ReadFriendlyName(guid);
            result.Add(new PowerSchemeInfo
            {
                Guid = guid.ToString("D"),
                Name = string.IsNullOrWhiteSpace(name) ? $"План {guid:D}" : name,
                IsActive = activeGuid.HasValue && guid == activeGuid.Value
            });
        }

        return result;
    }

    private static string ReadActivePlanNative()
    {
        var guid = ReadActiveGuid();
        return guid.HasValue ? ReadFriendlyName(guid.Value) : "Не удалось определить";
    }

    private static Guid? ReadActiveGuid()
    {
        IntPtr schemePtr = IntPtr.Zero;
        try
        {
            var status = PowerGetActiveScheme(IntPtr.Zero, out schemePtr);
            if (status != ErrorSuccess || schemePtr == IntPtr.Zero)
                return null;
            return Marshal.PtrToStructure<Guid>(schemePtr);
        }
        catch
        {
            return null;
        }
        finally
        {
            if (schemePtr != IntPtr.Zero)
                LocalFree(schemePtr);
        }
    }

    private static string ReadFriendlyName(Guid schemeGuid)
    {
        try
        {
            uint size = 0;
            var guid = schemeGuid;
            var status = PowerReadFriendlyName(IntPtr.Zero, ref guid, IntPtr.Zero, IntPtr.Zero, null, ref size);
            if ((status != ErrorSuccess && size == 0) || size == 0)
                return schemeGuid.ToString("D");

            var buffer = new byte[size];
            status = PowerReadFriendlyName(IntPtr.Zero, ref guid, IntPtr.Zero, IntPtr.Zero, buffer, ref size);
            if (status != ErrorSuccess)
                return schemeGuid.ToString("D");

            return Encoding.Unicode.GetString(buffer, 0, checked((int)size)).TrimEnd('\0').Trim();
        }
        catch
        {
            return schemeGuid.ToString("D");
        }
    }

    [DllImport("powrprof.dll", SetLastError = true)]
    private static extern uint PowerGetActiveScheme(IntPtr userRootPowerKey, out IntPtr activePolicyGuid);

    [DllImport("powrprof.dll", SetLastError = true)]
    private static extern uint PowerEnumerate(
        IntPtr rootPowerKey,
        IntPtr schemeGuid,
        IntPtr subGroupOfPowerSettingsGuid,
        uint accessFlags,
        uint index,
        [Out] byte[] buffer,
        ref uint bufferSize);

    [DllImport("powrprof.dll", SetLastError = true)]
    private static extern uint PowerReadFriendlyName(
        IntPtr rootPowerKey,
        ref Guid schemeGuid,
        IntPtr subGroupOfPowerSettingsGuid,
        IntPtr powerSettingGuid,
        [Out] byte[]? buffer,
        ref uint bufferSize);

    [DllImport("kernel32.dll")]
    private static extern IntPtr LocalFree(IntPtr hMem);
}
