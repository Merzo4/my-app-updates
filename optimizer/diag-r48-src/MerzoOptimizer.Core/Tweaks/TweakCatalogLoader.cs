using System.Text.Json;
using System.Text.Json.Serialization;

namespace MerzoOptimizer.Core.Tweaks;

public static class TweakCatalogLoader
{
    public static IReadOnlyList<TweakDefinition> Load(string path)
    {
        if (!File.Exists(path))
            return [];

        var options = new JsonSerializerOptions
        {
            PropertyNameCaseInsensitive = true,
            PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower
        };
        options.Converters.Add(new JsonStringEnumConverter());

        var json = File.ReadAllText(path);
        return JsonSerializer.Deserialize<List<TweakDefinition>>(json, options) ?? [];
    }
}
