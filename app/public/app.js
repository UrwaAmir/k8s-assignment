$(function () {
  const fmt = (x) => Number(x).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });

  function showError(msg) {
    $('#form-error').text(msg).removeClass('d-none');
  }
  function clearError() {
    $('#form-error').addClass('d-none').text('');
  }

  function validate(P, rate, n) {
    if (!(P > 0)) return 'Loan amount must be a positive number';
    if (!(rate > 0)) return 'Interest rate must be a positive number';
    if (!(n > 0) || !Number.isInteger(n)) return 'Tenure must be a positive whole number of months';
    return null;
  }

  function loadHistory() {
    $.getJSON('/api/history')
      .done(function (rows) {
        const $body = $('#history-body').empty();
        if (!rows.length) {
          $body.append($('<tr>').append($('<td colspan="6" class="text-muted">').text('No calculations yet.')));
          return;
        }
        rows.forEach(function (r) {
          const $tr = $('<tr>');
          $tr.append($('<td>').text(new Date(r.createdAt).toLocaleString()));
          $tr.append($('<td>').text(fmt(r.principal)));
          $tr.append($('<td>').text(r.rate));
          $tr.append($('<td>').text(r.months));
          $tr.append($('<td>').text(fmt(r.emi)));
          $tr.append($('<td>').text(r.servedBy));
          $body.append($tr);
        });
      })
      .fail(function () {
        $('#history-body').empty().append(
          $('<tr>').append($('<td colspan="6" class="text-danger">').text('Could not load history.'))
        );
      });
  }

  $('#emi-form').on('submit', function (e) {
    e.preventDefault(); // no postback
    clearError();

    const P = parseFloat($('#principal').val());
    const rate = parseFloat($('#rate').val());
    const n = parseFloat($('#months').val());

    const err = validate(P, rate, n);
    if (err) return showError(err);

    $('#calc-btn').prop('disabled', true);

    $.ajax({
      url: '/api/emi',
      method: 'POST',
      contentType: 'application/json',
      data: JSON.stringify({ P: P, rate: rate, n: n }),
      dataType: 'json'
    })
      .done(function (res) {
        $('#r-emi').text(fmt(res.emi));
        $('#r-total').text(fmt(res.totalPayment));
        $('#r-interest').text(fmt(res.totalInterest));
        $('#r-pod').text(res.servedBy);
        $('#r-ip').text(res.podIp);
        $('#result-empty').addClass('d-none');
        $('#result-content').removeClass('d-none');
        loadHistory();
      })
      .fail(function (xhr) {
        const msg = xhr.responseJSON && xhr.responseJSON.error ? xhr.responseJSON.error : 'Request failed';
        showError(msg);
      })
      .always(function () {
        $('#calc-btn').prop('disabled', false);
      });
  });

  loadHistory();
});
