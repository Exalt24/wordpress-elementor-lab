/*
 * The industry filter on the front page. A click on an industry button asks WordPress's admin-ajax for that industry's case study cards and swaps
 * the grid, with no page load. The server renders and escapes the cards; this file only moves them in. Without JavaScript the bar stays hidden and
 * the full grid is already on the page.
 */
jQuery(function ($) {
  var cfg = window.labCoreFilter;
  var $bar = $('.case-filter');
  var $grid = $('#lab-case-grid');
  if (!cfg || !$bar.length || !$grid.length) {
    return;
  }
  var $status = $('<p class="case-status" role="status"></p>').insertAfter($bar);
  var inFlight = null;

  function setPressed($button) {
    $bar.find('button').attr('aria-pressed', 'false');
    $button.attr('aria-pressed', 'true');
  }

  function request(industry) {
    return $.ajax({
      url: cfg.ajaxUrl,
      method: 'POST',
      dataType: 'json',
      timeout: 10000,
      data: { action: cfg.action, nonce: cfg.nonce, industry: industry }
    });
  }

  function fail() {
    $status.addClass('is-error').text('The case studies could not be loaded. Try again.');
  }

  function load($button) {
    if (inFlight) {
      inFlight.abort();
    }
    $grid.attr('aria-busy', 'true');
    $status.removeClass('is-error').text('Loading case studies...');
    var xhr = request($button.data('industry') || '');
    inFlight = xhr;
    xhr.done(function (res) {
      if (!res || !res.success || !res.data || typeof res.data.html !== 'string') {
        fail();
        return;
      }
      $grid.html(res.data.html);
      setPressed($button);
      $status.text(res.data.count + (res.data.count === 1 ? ' case study shown.' : ' case studies shown.'));
    });
    xhr.fail(function (_x, reason) {
      if (reason !== 'abort') {
        fail();
      }
    });
    xhr.always(function () {
      if (inFlight === xhr) {
        inFlight = null;
        $grid.attr('aria-busy', 'false');
      }
    });
  }

  $bar.prop('hidden', false);
  $bar.on('click', 'button', function () {
    var $button = $(this);
    if ($button.attr('aria-pressed') !== 'true') {
      load($button);
    }
  });
});
