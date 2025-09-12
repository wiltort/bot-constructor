(function($) {
    $(document).ready(function() {
        // Открываем ссылки "Добавить новый шаг" в новом окне
        $('a[href*="add-step/"]').on('click', function(e) {
            e.preventDefault();
            window.open($(this).attr('href'), '_blank', 'width=800,height=600');
        });
    });
})(django.jQuery);