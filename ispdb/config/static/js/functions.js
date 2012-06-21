function addWaterMark(textbox, watermarktext) {
    $(textbox).addClass("watermark").val(watermarktext);
    $(textbox).focus(function() {
        $(this).filter(function() {
            return $(this).val() == "" || $(this).val() == watermarktext
        }).removeClass("watermark").val("");
    });
    $(textbox).blur(function() {
        $(this).filter(function() {
            return $(this).val() == ""
        }).addClass("watermark").val(watermarktext);
    });
}
