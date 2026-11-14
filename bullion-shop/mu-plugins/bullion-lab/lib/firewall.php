<?php
namespace Bullion;

/**
 * A small request filter for what scanners ask a WordPress site for. It runs only on requests that reach WordPress, which is every request for a file that does
 * not exist, so it catches probes for secrets and backups without touching a real page, an image, the sitemap or robots.txt. It is a code level rule set, not a
 * network firewall, and it says nothing about who a visitor is: a crawler gets the same treatment as anyone else.
 */
final class Firewall
{
    /** Paths nobody should ask a public site for. Each is matched against the lower cased path. */
    private const PATH_PATTERNS = [
        '#(^|/)\.(env|git|svn|hg|htpasswd|ds_store)(/|$)#',
        '#(^|/)wp-config\.(php\.|txt|bak|old|save|orig)#',
        '#\.(sql|sqlite|bak|old|orig|swp|tar|tgz|gz|zip)$#',
        '#(^|/)(debug|error)\.log$#',
        '#(^|/)(phpinfo|info|test|shell|adminer)\.php$#',
        '#(^|/)wp-content/uploads/.*\.php$#',
    ];

    /** Names that attack tools announce themselves with. A tool can lie, so this stops the lazy ones only. */
    private const AGENT_PATTERN = '#(sqlmap|nikto|nmap|masscan|wpscan|acunetix|nessus|havij)#';

    /** The reason a request should be refused with a 403, or null to let it through. */
    public static function reason(string $path, string $userAgent): ?string
    {
        $p = strtolower(rawurldecode($path));
        foreach (self::PATH_PATTERNS as $re) {
            if (preg_match($re, $p)) {
                return 'path';
            }
        }
        if (preg_match(self::AGENT_PATTERN, strtolower($userAgent))) {
            return 'agent';
        }
        return null;
    }
}
