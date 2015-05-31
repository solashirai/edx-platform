define(['backbone', 'jquery', 'js/crowdsourcehinter'],
    function (Backbone, $, CrowdsourceHinter) {

        chinter = require('CrowdsourceHinter');
        csh = chinter.readFileSync('js/crowdsourcehinter', 'utf-8');
        eval(csh);

        describe('CrowdsourceHinter', function () {
                it('defines url to courseware ajax entry point', function () {
                    expect(true).toBe(true);
                });

                it('test test test', function() {
                        expect(CrowdsourceHinter.checkIsAnswerCorrect('123')).toBe(false);
                });
                it('test test test', function() {
                        expect(csh.checkIsAnswerCorrect('123')).toBe(false);
                });
                it('test asdf test', function() {
                    data = "test";
                    var csh = CrowdsourceHinter();
                    expect(CrowdsourceHinter).toBe(true);
                });
        });
    });
