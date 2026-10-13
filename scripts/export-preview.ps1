param()
$ErrorActionPreference = 'Stop'
$workspace = Split-Path $PSScriptRoot -Parent
$sourceRoot = Join-Path $workspace '.preview-public'
$previewRoot = Join-Path $workspace 'web-preview'
if (-not (Test-Path (Join-Path $sourceRoot 'zh/index.html'))) { throw 'Run hugo --destination .preview-public first.' }
foreach ($sourceFile in Get-ChildItem $sourceRoot -File -Recurse) {
    $relative = [IO.Path]::GetRelativePath($sourceRoot, $sourceFile.FullName)
    $target = Join-Path $previewRoot $relative
    New-Item -ItemType Directory -Path ([IO.Path]::GetDirectoryName($target)) -Force | Out-Null
    Copy-Item -LiteralPath $sourceFile.FullName -Destination $target -Force
}
foreach ($file in Get-ChildItem $previewRoot -Filter *.html -Recurse) {
    $html = Get-Content -LiteralPath $file.FullName -Raw
    $relative = [IO.Path]::GetRelativePath($previewRoot, $file.FullName).Replace('\', '/')
    $pageBase = [uri]('https://huijie-lian.github.io/' + $relative)
    $html = [regex]::Replace($html, '(?<attr>href|src)=(?:"(?<url>[^"]*)"|(?<url>[^\s>]+))', {
        param($match)
        $url = $match.Groups['url'].Value
        if ($url.StartsWith('#') -or $url -match '^(mailto:|tel:|data:|javascript:)') { return $match.Value }
        try { $uri = [uri]::new($pageBase, $url) } catch { return $match.Value }
        if ($uri.Host -notin @('huijie-lian.github.io', 'localhost', '127.0.0.1')) { return $match.Value }
        $path = [uri]::UnescapeDataString($uri.AbsolutePath.TrimStart('/'))
        if ($path.EndsWith('/') -or -not $path) { $path += 'index.html' }
        $link = [IO.Path]::GetRelativePath($file.DirectoryName, (Join-Path $previewRoot $path)).Replace('\', '/')
        return $match.Groups['attr'].Value + '="' + $link + $uri.Fragment + '"'
    })
    $html = [regex]::Replace($html, '\s+(integrity|crossorigin)=("[^"]*"|[^\s>]+)', '')
    Set-Content -LiteralPath $file.FullName -Value $html -Encoding utf8
}
Write-Output "Offline preview: $previewRoot\zh\index.html"
