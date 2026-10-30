# Cai dat SinkholeHome (Nhom 16) tren Windows (can Docker Desktop)
# Dung: .\install.ps1          (Pi-hole + Unbound)
#       .\install.ps1 -Vpn     (them WireGuard)
#       .\install.ps1 -App     (them backend + frontend)
param([switch]$Vpn, [switch]$App)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "==> Kiem tra Docker..."
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Host "Chua co Docker. Hay cai Docker Desktop: https://www.docker.com/products/docker-desktop/"
    exit 1
}
docker compose version | Out-Null

$profiles = @()
if ($Vpn) { $profiles += @("--profile", "vpn") }
if ($App) { $profiles += @("--profile", "app") }

Write-Host "==> Tao file .env..."
if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    $pass = Read-Host "Nhap mat khau Pi-hole"
    if ($pass) {
        (Get-Content ".env") -replace '^PIHOLE_PASSWORD=.*', "PIHOLE_PASSWORD=$pass" | Set-Content ".env"
    }
    if ($Vpn) {
        $hostName = Read-Host "Nhap IP public hoac ten mien cua may nay"
        (Get-Content ".env") -replace '^WG_HOST=.*', "WG_HOST=$hostName" | Set-Content ".env"
        $wgPass = Read-Host "Nhap mat khau trang quan ly WireGuard"
        $out = docker run --rm ghcr.io/wg-easy/wg-easy:14 wgpw $wgPass
        $hash = ($out -replace "^PASSWORD_HASH='(.*)'$", '$1') -replace '\$', '$$$$'
        (Get-Content ".env") -replace '^WG_PASSWORD_HASH=.*', ("WG_PASSWORD_HASH=" + $hash) | Set-Content ".env"
    }
} else {
    Write-Host ".env da ton tai, giu nguyen."
}

Write-Host "==> Khoi dong..."
docker compose @profiles up -d

Write-Host ""
Write-Host "Xong! Mo trinh duyet: http://localhost:<PIHOLE_WEB_PORT>/admin (xem trong file .env)"
