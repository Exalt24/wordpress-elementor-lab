<?php
// Moodle CLI helpers for the support lab, run inside the container: php /lab/lab.php <command> [args]
// Anything that Moodle's web service API cannot do (create an activity, set an access restriction, clear a lockout) goes through
// Moodle's own PHP functions here, the same functions the admin pages call. Output is one JSON document on one line.
define('CLI_SCRIPT', true);
foreach (['/bitnami/moodle/config.php', '/opt/bitnami/moodle/config.php'] as $c) {
    if (is_file($c)) { require($c); break; }
}
require_once($CFG->libdir . '/clilib.php');
require_once($CFG->dirroot . '/course/modlib.php');
require_once($CFG->dirroot . '/lib/enrollib.php');

function out($data) { echo json_encode($data), "\n"; }

$cmd = $argv[1] ?? '';
switch ($cmd) {
    case 'setup-ws':
        set_config('enablewebservices', 1);
        set_config('webserviceprotocols', 'rest');
        $functions = ['core_webservice_get_site_info', 'core_user_create_users', 'core_user_get_users_by_field', 'core_user_update_users',
            'core_course_create_courses', 'core_course_get_courses', 'core_course_update_courses', 'core_course_get_contents',
            'core_course_edit_module', 'core_enrol_get_users_courses', 'core_enrol_get_enrolled_users', 'enrol_manual_enrol_users',
            'enrol_manual_unenrol_users', 'core_course_get_courses_by_field', 'core_course_delete_courses', 'core_user_delete_users'];
        $svc = $DB->get_record('external_services', ['shortname' => 'support_lab']);
        if (!$svc) {
            $svc = (object)['name' => 'Support lab', 'shortname' => 'support_lab', 'enabled' => 1, 'restrictedusers' => 0,
                'component' => null, 'timecreated' => time(), 'timemodified' => time(), 'downloadfiles' => 0, 'uploadfiles' => 0];
            $svc->id = $DB->insert_record('external_services', $svc);
        }
        foreach ($functions as $f) {
            if (!$DB->record_exists('external_services_functions', ['externalserviceid' => $svc->id, 'functionname' => $f])) {
                $DB->insert_record('external_services_functions', (object)['externalserviceid' => $svc->id, 'functionname' => $f]);
            }
        }
        // Lockout rules the Tier 1 cases depend on: three failed logins lock the account for the window.
        set_config('lockoutthreshold', 3);
        set_config('lockoutwindow', 600);
        set_config('lockoutduration', 1800);
        // There is no mail server in the lab: with the email output on, the enrolment welcome message fails with "Message was not sent".
        $DB->set_field('message_processors', 'enabled', 0, ['name' => 'email']);
        // The "Find your way around" user tour covers the page in screenshots.
        $DB->execute('UPDATE {tool_usertours_tours} SET enabled = 0');
        out(['service' => (int)$svc->id, 'functions' => count($functions), 'lockoutthreshold' => 3]);
        break;

    case 'make-token':   // make-token <username>: Site administration > Server > Manage tokens. The token endpoint refuses site admins by design.
        $u = $DB->get_record('user', ['username' => $argv[2]], '*', MUST_EXIST);
        $svc = $DB->get_record('external_services', ['shortname' => 'support_lab'], '*', MUST_EXIST);
        $token = $DB->get_field_select('external_tokens', 'token', 'userid = ? AND externalserviceid = ? AND tokentype = ?',
            [$u->id, $svc->id, EXTERNAL_TOKEN_PERMANENT], IGNORE_MULTIPLE);
        if (!$token) {
            $token = \core_external\util::generate_token(EXTERNAL_TOKEN_PERMANENT, $svc, $u->id, context_system::instance());
        }
        out(['token' => $token]);
        break;

    case 'seed-assign':   // seed-assign <courseid> <name> [availablefrom-unixtime|0] [hidden 0|1]
        $courseid = (int)$argv[2]; $name = $argv[3]; $from = (int)($argv[4] ?? 0); $hidden = (int)($argv[5] ?? 0);
        $course = get_course($courseid);
        $info = new stdClass();
        $info->modulename = 'assign'; $info->module = $DB->get_field('modules', 'id', ['name' => 'assign']);
        $info->course = $courseid; $info->section = 1; $info->visible = $hidden ? 0 : 1; $info->visibleoncoursepage = 1;
        $info->name = $name; $info->intro = 'Invented assignment for the support lab.'; $info->introformat = FORMAT_HTML;
        $info->submissiondrafts = 0; $info->requiresubmissionstatement = 0; $info->sendnotifications = 0; $info->sendlatenotifications = 0;
        $info->duedate = time() + 14 * 86400; $info->cutoffdate = 0; $info->gradingduedate = 0; $info->allowsubmissionsfromdate = 0;
        $info->grade = 100; $info->teamsubmission = 0; $info->requireallteammemberssubmit = 0; $info->blindmarking = 0;
        $info->markingworkflow = 0; $info->markingallocation = 0; $info->cmidnumber = ''; $info->completion = 0; $info->maxattempts = -1;
        $info->attemptreopenmethod = 'none'; $info->hidegrader = 0;
        $info->assignsubmission_onlinetext_enabled = 1; $info->assignfeedback_comments_enabled = 1;
        if ($from > 0) {
            $info->availabilityconditionsjson = json_encode(['op' => '&', 'c' => [['type' => 'date', 'd' => '>=', 't' => $from]], 'showc' => [true]]);
        }
        $cm = add_moduleinfo($info, $course);
        out(['cmid' => (int)$cm->coursemodule, 'name' => $name]);
        break;

    case 'availability':   // availability <cmid>: what the activity settings page shows under Restrict access
        $cm = $DB->get_record('course_modules', ['id' => (int)$argv[2]], '*', MUST_EXIST);
        out(['cmid' => (int)$cm->id, 'visible' => (int)$cm->visible, 'availability' => $cm->availability ? json_decode($cm->availability) : null]);
        break;

    case 'set-availability-from':   // set-availability-from <cmid> <unixtime>
        $cm = $DB->get_record('course_modules', ['id' => (int)$argv[2]], '*', MUST_EXIST);
        $json = json_encode(['op' => '&', 'c' => [['type' => 'date', 'd' => '>=', 't' => (int)$argv[3]]], 'showc' => [true]]);
        $DB->set_field('course_modules', 'availability', $json, ['id' => $cm->id]);
        rebuild_course_cache($cm->course, true);
        out(['cmid' => (int)$cm->id, 'availability' => json_decode($json)]);
        break;

    case 'lockout-status':   // lockout-status <username>: the lockout preferences and the last failed logins Moodle logged
        $u = $DB->get_record('user', ['username' => $argv[2]], '*', MUST_EXIST);
        $prefs = [];
        foreach (['login_failed_count', 'login_failed_count_since_success', 'login_failed_last', 'login_lockout', 'login_lockout_ignored'] as $p) {
            $v = get_user_preferences($p, null, $u);
            if ($v !== null) { $prefs[$p] = (int)$v; }
        }
        $rows = $DB->get_records_sql(
            'SELECT id, eventname, timecreated, other FROM {logstore_standard_log} WHERE eventname = :e AND userid = :u ORDER BY id DESC',
            ['e' => '\\core\\event\\user_login_failed', 'u' => $u->id], 0, 10);
        $events = [];
        foreach ($rows as $r) {
            $o = json_decode($r->other, true);
            if (!is_array($o)) { $o = @unserialize($r->other); }
            $o = is_array($o) ? $o : [];
            $events[] = ['time' => (int)$r->timecreated, 'reason' => (int)($o['reason'] ?? -1)];
        }
        out(['userid' => (int)$u->id, 'locked' => (bool)get_user_preferences('login_lockout', 0, $u), 'preferences' => $prefs,
            'failed_login_events' => $events, 'threshold' => (int)$CFG->lockoutthreshold, 'window' => (int)$CFG->lockoutwindow]);
        break;

    case 'unlock':   // unlock <username>: the Unlock action of the user list in Site administration
        $u = $DB->get_record('user', ['username' => $argv[2]], '*', MUST_EXIST);
        login_unlock_account($u);
        out(['userid' => (int)$u->id, 'locked' => (bool)get_user_preferences('login_lockout', 0, $u)]);
        break;

    default:
        fwrite(STDERR, "unknown command\n");
        exit(2);
}
