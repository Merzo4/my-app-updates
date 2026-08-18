using System.Globalization;
using Microsoft.Win32;
using MerzoOptimizer.Core.Snapshots;
using MerzoOptimizer.Core.Tweaks;

namespace MerzoOptimizer.Windows.RegistryAccess;

internal sealed class RegistryTweakAccessor
{
    public RegistryValueSnapshot Capture(RegistryTweakAction action)
    {
        using var baseKey = OpenBaseKey(action.Hive);
        using var key = baseKey.OpenSubKey(action.KeyPath, writable: false);

        if (key is null || !key.GetValueNames().Contains(action.ValueName, StringComparer.OrdinalIgnoreCase))
        {
            return new RegistryValueSnapshot
            {
                Hive = action.Hive,
                KeyPath = action.KeyPath,
                ValueName = action.ValueName,
                Existed = false
            };
        }

        var kind = key.GetValueKind(action.ValueName);
        var value = key.GetValue(
            action.ValueName,
            defaultValue: null,
            RegistryValueOptions.DoNotExpandEnvironmentNames);

        return EncodeSnapshot(action, kind, value);
    }

    public bool MatchesDesiredValue(RegistryTweakAction action)
    {
        var current = Capture(action);
        if (action.Mode == RegistryTweakActionMode.DeleteValue)
            return !current.Existed;

        if (!current.Existed || current.ValueType is null)
            return false;

        return action.ValueType switch
        {
            RegistryTweakValueType.DWord or RegistryTweakValueType.QWord =>
                current.IntegerValue == action.IntegerValue && current.ValueType == action.ValueType,
            RegistryTweakValueType.String or RegistryTweakValueType.ExpandString =>
                string.Equals(current.StringValue, action.StringValue, StringComparison.Ordinal) && current.ValueType == action.ValueType,
            _ => false
        };
    }

    public void Apply(RegistryTweakAction action)
    {
        using var baseKey = OpenBaseKey(action.Hive);

        if (action.Mode == RegistryTweakActionMode.DeleteValue)
        {
            using var existingKey = baseKey.OpenSubKey(action.KeyPath, writable: true);
            existingKey?.DeleteValue(action.ValueName, throwOnMissingValue: false);
            return;
        }

        using var key = baseKey.CreateSubKey(action.KeyPath, writable: true)
            ?? throw new InvalidOperationException($"Не удалось открыть/создать ключ {action.Hive}\\{action.KeyPath}.");

        switch (action.ValueType)
        {
            case RegistryTweakValueType.DWord:
                key.SetValue(action.ValueName, checked((int)(action.IntegerValue ?? 0)), RegistryValueKind.DWord);
                break;
            case RegistryTweakValueType.QWord:
                key.SetValue(action.ValueName, action.IntegerValue ?? 0L, RegistryValueKind.QWord);
                break;
            case RegistryTweakValueType.String:
                key.SetValue(action.ValueName, action.StringValue ?? string.Empty, RegistryValueKind.String);
                break;
            case RegistryTweakValueType.ExpandString:
                key.SetValue(action.ValueName, action.StringValue ?? string.Empty, RegistryValueKind.ExpandString);
                break;
            default:
                throw new NotSupportedException($"Тип реестра {action.ValueType} пока нельзя применять через R20.");
        }
    }

    public void Restore(RegistryValueSnapshot entry)
    {
        using var baseKey = OpenBaseKey(entry.Hive);

        if (!entry.Existed)
        {
            using var existingKey = baseKey.OpenSubKey(entry.KeyPath, writable: true);
            existingKey?.DeleteValue(entry.ValueName, throwOnMissingValue: false);
            return;
        }

        using var key = baseKey.CreateSubKey(entry.KeyPath, writable: true)
            ?? throw new InvalidOperationException($"Не удалось открыть/создать ключ {entry.Hive}\\{entry.KeyPath} для восстановления.");

        if (entry.ValueType is null)
            throw new InvalidOperationException("Snapshot не содержит тип существовавшего значения реестра.");

        switch (entry.ValueType.Value)
        {
            case RegistryTweakValueType.DWord:
                key.SetValue(entry.ValueName, checked((int)(entry.IntegerValue ?? 0)), RegistryValueKind.DWord);
                break;
            case RegistryTweakValueType.QWord:
                key.SetValue(entry.ValueName, entry.IntegerValue ?? 0L, RegistryValueKind.QWord);
                break;
            case RegistryTweakValueType.String:
                key.SetValue(entry.ValueName, entry.StringValue ?? string.Empty, RegistryValueKind.String);
                break;
            case RegistryTweakValueType.ExpandString:
                key.SetValue(entry.ValueName, entry.StringValue ?? string.Empty, RegistryValueKind.ExpandString);
                break;
            case RegistryTweakValueType.MultiString:
                key.SetValue(entry.ValueName, entry.MultiStringValue ?? [], RegistryValueKind.MultiString);
                break;
            case RegistryTweakValueType.Binary:
                key.SetValue(entry.ValueName,
                    string.IsNullOrWhiteSpace(entry.BinaryBase64) ? Array.Empty<byte>() : Convert.FromBase64String(entry.BinaryBase64),
                    RegistryValueKind.Binary);
                break;
            default:
                throw new NotSupportedException($"Тип {entry.ValueType} из snapshot пока не поддерживается RestoreEngine.");
        }
    }

    public static string Describe(RegistryValueSnapshot entry)
    {
        if (!entry.Existed)
            return "<не существовало>";

        return entry.ValueType switch
        {
            RegistryTweakValueType.DWord => $"DWORD:{entry.IntegerValue}",
            RegistryTweakValueType.QWord => $"QWORD:{entry.IntegerValue}",
            RegistryTweakValueType.String => $"STRING:{entry.StringValue}",
            RegistryTweakValueType.ExpandString => $"EXPAND:{entry.StringValue}",
            RegistryTweakValueType.MultiString => $"MULTI:{string.Join(" | ", entry.MultiStringValue ?? [])}",
            RegistryTweakValueType.Binary => $"BINARY:{entry.BinaryBase64}",
            _ => "<неизвестно>"
        };
    }

    public static string Describe(RegistryTweakAction action)
    {
        if (action.Mode == RegistryTweakActionMode.DeleteValue)
            return "<удалить значение>";

        return action.ValueType switch
        {
        RegistryTweakValueType.DWord => $"DWORD:{action.IntegerValue}",
        RegistryTweakValueType.QWord => $"QWORD:{action.IntegerValue}",
        RegistryTweakValueType.String => $"STRING:{action.StringValue}",
            RegistryTweakValueType.ExpandString => $"EXPAND:{action.StringValue}",
            _ => action.ValueType.ToString()
        };
    }

    private static RegistryValueSnapshot EncodeSnapshot(
        RegistryTweakAction action,
        RegistryValueKind kind,
        object? value)
    {
        var type = kind switch
        {
            RegistryValueKind.DWord => RegistryTweakValueType.DWord,
            RegistryValueKind.QWord => RegistryTweakValueType.QWord,
            RegistryValueKind.String => RegistryTweakValueType.String,
            RegistryValueKind.ExpandString => RegistryTweakValueType.ExpandString,
            RegistryValueKind.MultiString => RegistryTweakValueType.MultiString,
            RegistryValueKind.Binary or RegistryValueKind.None => RegistryTweakValueType.Binary,
            _ => throw new NotSupportedException($"Неизвестный RegistryValueKind: {kind}.")
        };

        return new RegistryValueSnapshot
        {
            Hive = action.Hive,
            KeyPath = action.KeyPath,
            ValueName = action.ValueName,
            Existed = true,
            ValueType = type,
            IntegerValue = type is RegistryTweakValueType.DWord or RegistryTweakValueType.QWord
                ? Convert.ToInt64(value, CultureInfo.InvariantCulture)
                : null,
            StringValue = type is RegistryTweakValueType.String or RegistryTweakValueType.ExpandString
                ? Convert.ToString(value, CultureInfo.InvariantCulture)
                : null,
            MultiStringValue = type == RegistryTweakValueType.MultiString ? value as string[] : null,
            BinaryBase64 = type == RegistryTweakValueType.Binary && value is byte[] bytes
                ? Convert.ToBase64String(bytes)
                : null
        };
    }

    private static RegistryKey OpenBaseKey(RegistryHiveScope hive)
    {
        var registryHive = hive switch
        {
            RegistryHiveScope.LocalMachine => RegistryHive.LocalMachine,
            RegistryHiveScope.CurrentUser => RegistryHive.CurrentUser,
            _ => throw new ArgumentOutOfRangeException(nameof(hive), hive, null)
        };

        var view = Environment.Is64BitOperatingSystem
            ? RegistryView.Registry64
            : RegistryView.Registry32;

        return RegistryKey.OpenBaseKey(registryHive, view);
    }
}
