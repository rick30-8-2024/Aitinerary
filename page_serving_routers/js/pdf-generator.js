/**
 * PDF Generator module for Aitinerary using pdfmake
 * Generates beautifully formatted PDF itineraries with custom fonts
 */

const PDFGenerator = {
    fontsLoaded: false,

    async loadFonts() {
        if (this.fontsLoaded) return;

        try {
            const [playfairResponse, taraResponse] = await Promise.all([
                fetch('/fonts/PlayfairDisplay-VariableFont_wght.ttf'),
                fetch('/fonts/TaraType.ttf')
            ]);

            const playfairBuffer = await playfairResponse.arrayBuffer();
            const taraBuffer = await taraResponse.arrayBuffer();

            const playfairBase64 = this.arrayBufferToBase64(playfairBuffer);
            const taraBase64 = this.arrayBufferToBase64(taraBuffer);

            pdfMake.vfs = pdfMake.vfs || {};
            pdfMake.vfs['PlayfairDisplay.ttf'] = playfairBase64;
            pdfMake.vfs['TaraType.ttf'] = taraBase64;

            pdfMake.fonts = {
                PlayfairDisplay: {
                    normal: 'PlayfairDisplay.ttf',
                    bold: 'PlayfairDisplay.ttf',
                    italics: 'PlayfairDisplay.ttf',
                    bolditalics: 'PlayfairDisplay.ttf'
                },
                TaraType: {
                    normal: 'TaraType.ttf',
                    bold: 'TaraType.ttf',
                    italics: 'TaraType.ttf',
                    bolditalics: 'TaraType.ttf'
                },
                Roboto: {
                    normal: 'Roboto-Regular.ttf',
                    bold: 'Roboto-Medium.ttf',
                    italics: 'Roboto-Italic.ttf',
                    bolditalics: 'Roboto-MediumItalic.ttf'
                }
            };

            this.fontsLoaded = true;
        } catch (error) {
            console.error('Failed to load custom fonts, using Roboto fallback:', error);
            pdfMake.fonts = {
                Roboto: {
                    normal: 'Roboto-Regular.ttf',
                    bold: 'Roboto-Medium.ttf',
                    italics: 'Roboto-Italic.ttf',
                    bolditalics: 'Roboto-MediumItalic.ttf'
                }
            };
            this.fontsLoaded = true;
        }
    },

    arrayBufferToBase64(buffer) {
        let binary = '';
        const bytes = new Uint8Array(buffer);
        const len = bytes.byteLength;
        for (let i = 0; i < len; i++) {
            binary += String.fromCharCode(bytes[i]);
        }
        return btoa(binary);
    },

    formatCurrency(amount, currency = 'USD') {
        return new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: currency,
            minimumFractionDigits: 0,
            maximumFractionDigits: 0
        }).format(amount || 0);
    },

    toTitleCase(str) {
        if (!str) return '';
        return str.toLowerCase().replace(/\b\w/g, char => char.toUpperCase());
    },

    formatDate(dateStr) {
        if (!dateStr) return '';
        const date = new Date(dateStr);
        return date.toLocaleDateString('en-US', {
            weekday: 'long',
            year: 'numeric',
            month: 'long',
            day: 'numeric'
        });
    },

    getDefaultFont() {
        return this.fontsLoaded && pdfMake.vfs['PlayfairDisplay.ttf'] ? 'PlayfairDisplay' : 'Roboto';
    },

    getHeaderFont() {
        return this.fontsLoaded && pdfMake.vfs['TaraType.ttf'] ? 'TaraType' : 'Roboto';
    },

    getStyles() {
        const defaultFont = this.getDefaultFont();
        const headerFont = this.getHeaderFont();

        return {
            header: {
                font: defaultFont,
                fontSize: 28,
                bold: true,
                color: '#0b0b0f',
                margin: [0, 0, 0, 8]
            },
            subheader: {
                font: defaultFont,
                fontSize: 18,
                bold: true,
                color: '#0b0b0f',
                margin: [0, 20, 0, 8],
                alignment: 'center'
            },
            sectionTitle: {
                font: defaultFont,
                fontSize: 16,
                bold: true,
                color: '#0b0b0f',
                margin: [0, 15, 0, 8],
                alignment: 'center'
            },
            dayHeader: {
                font: defaultFont,
                fontSize: 14,
                bold: true,
                color: '#0b0b0f',
                margin: [0, 12, 0, 6],
                alignment: 'center'
            },
            activityTitle: {
                font: defaultFont,
                fontSize: 11,
                bold: true,
                color: '#0b0b0f'
            },
            body: {
                font: defaultFont,
                fontSize: 10,
                color: '#333333',
                lineHeight: 1.4
            },
            small: {
                font: defaultFont,
                fontSize: 9,
                color: '#666666'
            },
            muted: {
                font: defaultFont,
                fontSize: 9,
                color: '#888888',
                italics: true
            },
            tocItem: {
                font: defaultFont,
                fontSize: 10,
                color: '#0b0b0f',
                margin: [0, 3, 0, 3]
            },
            budgetLabel: {
                font: defaultFont,
                fontSize: 10,
                color: '#555555'
            },
            budgetValue: {
                font: defaultFont,
                fontSize: 10,
                bold: true,
                color: '#0b0b0f',
                alignment: 'right'
            },
            budgetTotal: {
                font: defaultFont,
                fontSize: 12,
                bold: true,
                color: '#0b0b0f'
            },
            tableHeader: {
                font: defaultFont,
                fontSize: 10,
                bold: true,
                color: '#ffffff',
                fillColor: '#0b0b0f'
            },
            footerText: {
                font: defaultFont,
                fontSize: 8,
                color: '#888888',
                alignment: 'center'
            },
            headerText: {
                font: headerFont,
                fontSize: 10,
                color: '#0b0b0f',
                bold: true
            },
            gemBadge: {
                font: defaultFont,
                fontSize: 8,
                color: '#7c3aed',
                bold: true
            },
            warningText: {
                font: defaultFont,
                fontSize: 9,
                color: '#dc2626'
            },
            tipText: {
                font: defaultFont,
                fontSize: 9,
                color: '#059669'
            },
            listItem: {
                font: defaultFont,
                fontSize: 10,
                color: '#333333',
                margin: [10, 2, 0, 2]
            }
        };
    },

    createHeader() {
        return {
            columns: [
                {
                    text: 'AITINERARY',
                    style: 'headerText',
                    margin: [40, 15, 0, 0]
                },
                {
                    text: '',
                    width: '*'
                }
            ]
        };
    },

    createFooter(currentPage, pageCount) {
        return {
            columns: [
                {
                    text: 'Created by Aitinerary',
                    style: 'footerText',
                    margin: [40, 0, 0, 0],
                    alignment: 'left'
                },
                {
                    text: `Page ${currentPage} of ${pageCount}`,
                    style: 'footerText',
                    margin: [0, 0, 40, 0],
                    alignment: 'right'
                }
            ],
            margin: [0, 10, 0, 0]
        };
    },

    getYouTubeVideoId(url) {
        const patterns = [
            /(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([a-zA-Z0-9_-]{11})/,
            /youtube\.com\/shorts\/([a-zA-Z0-9_-]{11})/
        ];
        
        for (const pattern of patterns) {
            const match = url.match(pattern);
            if (match) return match[1];
        }
        return null;
    },

    createTitlePage(data) {
        const destination = this.toTitleCase(data.destination) +
            (data.country ? `, ${this.toTitleCase(data.country)}` : '');

        const startDate = data.days && data.days.length > 0 && data.days[0].date
            ? this.formatDate(data.days[0].date)
            : '';

        const content = [
            { text: '\n\n\n' },
            {
                text: this.toTitleCase(data.title),
                style: 'header',
                alignment: 'center'
            },
            {
                text: destination,
                fontSize: 14,
                color: '#555555',
                alignment: 'center',
                margin: [0, 5, 0, 5]
            },
            {
                text: `${data.days.length} Days`,
                fontSize: 12,
                color: '#666666',
                alignment: 'center',
                margin: [0, 0, 0, 5]
            }
        ];

        if (startDate) {
            content.push({
                text: `Starting ${startDate}`,
                fontSize: 10,
                color: '#888888',
                alignment: 'center',
                margin: [0, 0, 0, 20]
            });
        } else {
            content.push({ text: '\n' });
        }

        content.push({
            canvas: [
                {
                    type: 'line',
                    x1: 150, y1: 0,
                    x2: 365, y2: 0,
                    lineWidth: 1,
                    lineColor: '#cccccc'
                }
            ],
            margin: [0, 10, 0, 20]
        });

        content.push({
            text: data.summary || '',
            style: 'body',
            alignment: 'center',
            margin: [40, 0, 40, 0]
        });

        if (data.youtube_urls && data.youtube_urls.length > 0) {
            content.push({
                canvas: [
                    {
                        type: 'line',
                        x1: 150, y1: 0,
                        x2: 365, y2: 0,
                        lineWidth: 1,
                        lineColor: '#cccccc'
                    }
                ],
                margin: [0, 30, 0, 20]
            });

            content.push({
                text: 'Generated from YouTube Videos',
                fontSize: 12,
                bold: true,
                color: '#555555',
                alignment: 'center',
                margin: [0, 0, 0, 12]
            });

            content.push({
                text: data.youtube_urls.map(url => url).join('\n'),
                fontSize: 10,
                color: '#666666',
                alignment: 'center',
                margin: [40, 0, 40, 0],
                lineHeight: 1.5
            });
        }

        return content;
    },

    createBudgetSummary(data) {
        const breakdown = data.budget_breakdown || {};
        const categories = [
            { key: 'food', label: 'Food & Dining', icon: '' },
            { key: 'activities', label: 'Activities', icon: '' },
            { key: 'transportation', label: 'Transportation', icon: '' },
            { key: 'shopping', label: 'Shopping', icon: '' },
            { key: 'miscellaneous', label: 'Miscellaneous', icon: '' }
        ];

        const budgetRows = categories
            .filter(cat => breakdown[cat.key] > 0)
            .map(cat => [
                { text: cat.label, style: 'budgetLabel' },
                { text: this.formatCurrency(breakdown[cat.key], data.currency), style: 'budgetValue' }
            ]);

        if (breakdown.subtotal_without_accommodation > 0) {
            budgetRows.push([
                { text: 'Subtotal (excl. stay)', style: 'budgetLabel', bold: true },
                { text: this.formatCurrency(breakdown.subtotal_without_accommodation, data.currency), style: 'budgetValue' }
            ]);
        }

        if (breakdown.accommodation_budget > 0) {
            budgetRows.push([
                { text: 'Budget for Accommodation', style: 'budgetLabel' },
                { text: this.formatCurrency(breakdown.accommodation_budget, data.currency), style: 'budgetValue' }
            ]);
        }

        const content = [
            { text: '', pageBreak: 'after' },
            { text: 'Budget Summary', style: 'subheader' },
            {
                table: {
                    widths: ['*', 'auto'],
                    body: [
                        ...budgetRows,
                        [
                            { text: 'Total Estimated Budget', style: 'budgetTotal', margin: [0, 8, 0, 0] },
                            { text: this.formatCurrency(data.total_budget_estimate, data.currency), style: 'budgetTotal', alignment: 'right', margin: [0, 8, 0, 0] }
                        ]
                    ]
                },
                layout: {
                    hLineWidth: function (i, node) {
                        return (i === node.table.body.length - 1) ? 1 : 0;
                    },
                    vLineWidth: function () { return 0; },
                    hLineColor: function () { return '#cccccc'; },
                    paddingTop: function () { return 4; },
                    paddingBottom: function () { return 4; }
                },
                margin: [0, 10, 0, 10]
            }
        ];

        if (data.accommodation_note) {
            content.push({
                text: data.accommodation_note,
                style: 'muted',
                margin: [0, 5, 0, 15]
            });
        }

        return content;
    },

    createTableOfContents(data) {
        const tocContent = [];

        tocContent.push({ text: 'Budget Summary', style: 'tocItem', alignment: 'center' });
        tocContent.push({ text: 'Table of Contents', style: 'tocItem', alignment: 'center' });

        data.days.forEach(day => {
            tocContent.push({
                text: [
                    { text: `Day ${day.day_number}: `, bold: true },
                    { text: this.toTitleCase(day.theme) }
                ],
                style: 'tocItem',
                alignment: 'center'
            });
        });

        tocContent.push({ text: 'Travel Tips', style: 'tocItem', alignment: 'center' });
        tocContent.push({ text: 'Packing Suggestions', style: 'tocItem', alignment: 'center' });
        tocContent.push({ text: 'Useful Phrases', style: 'tocItem', alignment: 'center' });

        return [
            { text: '', pageBreak: 'after' },
            { text: 'Table of Contents', style: 'subheader' },
            {
                stack: tocContent,
                margin: [0, 10, 0, 20]
            },
            { text: '', pageBreak: 'after' }
        ];
    },

    createDayContent(day, data) {
        const content = [];

        content.push({
            table: {
                widths: ['*'],
                body: [[
                    {
                        stack: [
                            {
                                text: `Day ${day.day_number} - ${this.toTitleCase(day.theme)}`,
                                style: 'dayHeader',
                                alignment: 'center',
                                margin: [0, 8, 0, 5]
                            },
                            {
                                text: this.formatCurrency(day.total_estimated_cost, data.currency),
                                fontSize: 11,
                                bold: true,
                                color: '#0b0b0f',
                                alignment: 'center',
                                margin: [0, 0, 0, 8]
                            }
                        ],
                        fillColor: '#f0f0f0'
                    }
                ]]
            },
            layout: {
                hLineWidth: function () { return 0; },
                vLineWidth: function () { return 0; },
                paddingLeft: function () { return 10; },
                paddingRight: function () { return 10; },
                paddingTop: function () { return 5; },
                paddingBottom: function () { return 5; }
            },
            margin: [0, 15, 0, 10]
        });

        if (day.date) {
            content.push({
                text: this.formatDate(day.date),
                style: 'small',
                margin: [0, 0, 0, 5]
            });
        }

        if (day.summary) {
            content.push({
                text: day.summary,
                style: 'body',
                margin: [0, 0, 0, 10]
            });
        }

        if (day.activities && day.activities.length > 0) {
            day.activities.forEach((activity, index) => {
                const activityContent = this.createActivityContent(activity, data, index > 0);
                activityContent.forEach(item => content.push(item));
            });
        }

        if (day.meals && day.meals.length > 0) {
            content.push({
                text: 'Meal Recommendations',
                style: 'sectionTitle',
                alignment: 'center',
                margin: [0, 15, 0, 8]
            });

            day.meals.forEach(meal => {
                content.push(this.createMealContent(meal, data));
            });
        }

        return content;
    },

    createActivityContent(activity, data, addSeparator) {
        const content = [];

        if (addSeparator) {
            content.push({
                canvas: [
                    {
                        type: 'line',
                        x1: 0, y1: 0,
                        x2: 515, y2: 0,
                        lineWidth: 0.5,
                        lineColor: '#e5e5e5'
                    }
                ],
                margin: [0, 8, 0, 8]
            });
        }

        const titleParts = [];
        if (activity.is_hidden_gem) {
            titleParts.push({ text: '[Hidden Gem] ', style: 'gemBadge' });
        }

        const placeName = this.toTitleCase(activity.place_name);
        const activityTitle = activity.event_name
            ? `${placeName} - ${this.toTitleCase(activity.event_name)}`
            : placeName;

        titleParts.push({ text: activityTitle, style: 'activityTitle' });

        content.push({
            columns: [
                {
                    width: 70,
                    stack: [
                        { text: activity.time_slot || '', style: 'small', bold: true },
                        { text: activity.estimated_duration || '', style: 'muted' }
                    ]
                },
                {
                    width: '*',
                    stack: [
                        { text: titleParts },
                        { text: activity.description || '', style: 'body', margin: [0, 3, 0, 5] },
                        this.createActivityMeta(activity, data)
                    ]
                }
            ],
            margin: [0, 5, 0, 5]
        });

        if (activity.tips && activity.tips.length > 0) {
            content.push({
                stack: [
                    { text: 'Tips:', style: 'tipText', bold: true, margin: [70, 0, 0, 2] },
                    {
                        ul: activity.tips,
                        style: 'tipText',
                        margin: [80, 0, 0, 5]
                    }
                ]
            });
        }

        if (activity.warnings && activity.warnings.length > 0) {
            content.push({
                stack: [
                    { text: 'Warnings:', style: 'warningText', bold: true, margin: [70, 0, 0, 2] },
                    {
                        ul: activity.warnings,
                        style: 'warningText',
                        margin: [80, 0, 0, 5]
                    }
                ]
            });
        }

        return content;
    },

    createActivityMeta(activity, data) {
        const metaParts = [];

        const costText = activity.cost_unknown
            ? 'Price not confirmed'
            : this.formatCurrency(activity.estimated_cost, data.currency);
        metaParts.push(costText);

        if (activity.travel_time_from_previous) {
            metaParts.push(activity.travel_time_from_previous);
        }

        if (activity.transport_mode) {
            let transportText = activity.transport_mode;
            if (activity.transport_cost_unknown) {
                transportText += ' (Price not confirmed)';
            } else if (activity.transport_cost) {
                transportText += ` - ${this.formatCurrency(activity.transport_cost, data.currency)}`;
            }
            metaParts.push(transportText);
        }

        if (activity.booking_required) {
            metaParts.push('Booking required');
        }

        return {
            text: metaParts.join('  |  '),
            style: 'small',
            margin: [0, 0, 0, 3]
        };
    },

    createMealContent(meal, data) {
        const mealTypes = {
            'breakfast': 'Breakfast',
            'lunch': 'Lunch',
            'dinner': 'Dinner',
            'snack': 'Snack'
        };

        const mealType = mealTypes[meal.meal_type] || 'Meal';
        const titleParts = [];

        if (meal.is_local_delicacy) {
            titleParts.push({ text: '[Local Delicacy] ', style: 'gemBadge' });
        }
        titleParts.push({ text: this.toTitleCase(meal.place_name), style: 'activityTitle' });

        const metaParts = [];
        const costText = meal.cost_unknown
            ? 'Price not confirmed'
            : `${this.formatCurrency(meal.estimated_cost, data.currency)}/person`;
        metaParts.push(costText);

        if (meal.recommendation_reason) {
            metaParts.push(meal.recommendation_reason);
        }

        const description = [meal.cuisine, meal.dietary_notes].filter(Boolean).join(' | ');

        return {
            columns: [
                {
                    width: 70,
                    text: mealType,
                    fontSize: 9,
                    bold: true,
                    color: '#666666',
                    margin: [0, 2, 0, 0]
                },
                {
                    width: '*',
                    stack: [
                        { text: titleParts },
                        description ? { text: description, style: 'small', margin: [0, 2, 0, 3] } : {},
                        { text: metaParts.join('  |  '), style: 'small' }
                    ]
                }
            ],
            margin: [0, 5, 0, 8]
        };
    },

    createTipsSection(tips) {
        if (!tips || tips.length === 0) return [];

        const tipItems = tips.map(tip => ({
            text: tip,
            style: 'listItem',
            alignment: 'center',
            margin: [20, 3, 20, 3]
        }));

        return [
            { text: 'Travel Tips', style: 'subheader', alignment: 'center', pageBreak: 'before' },
            {
                stack: tipItems,
                margin: [0, 10, 0, 20]
            }
        ];
    },

    createPackingSection(items) {
        if (!items || items.length === 0) return [];

        const packingItems = items.map(item => ({
            text: item,
            style: 'listItem',
            alignment: 'center',
            margin: [20, 3, 20, 3]
        }));

        return [
            { text: 'Packing Suggestions', style: 'subheader', alignment: 'center' },
            {
                stack: packingItems,
                margin: [0, 10, 0, 20]
            }
        ];
    },

    createPhrasesSection(phrases) {
        if (!phrases || phrases.length === 0) return [];

        const phraseItems = phrases.map(phrase => ({
            text: phrase,
            style: 'listItem',
            alignment: 'center',
            margin: [20, 3, 20, 3]
        }));

        return [
            { text: 'Useful Phrases', style: 'subheader', alignment: 'center' },
            {
                stack: phraseItems,
                margin: [0, 10, 0, 20]
            }
        ];
    },

    async generatePDF(data) {
        await this.loadFonts();

        const content = [];
        const defaultFont = this.getDefaultFont();

        content.push(...this.createTitlePage(data));
        content.push(...this.createBudgetSummary(data));
        content.push(...this.createTableOfContents(data));

        data.days.forEach((day, index) => {
            if (index > 0) {
                content.push({ text: '', pageBreak: 'before' });
            }
            content.push(...this.createDayContent(day, data));
        });

        content.push(...this.createTipsSection(data.general_tips));
        content.push(...this.createPackingSection(data.packing_suggestions));
        content.push(...this.createPhrasesSection(data.language_phrases));

        const docDefinition = {
            pageSize: 'A4',
            pageMargins: [40, 60, 40, 50],
            header: (currentPage, pageCount) => this.createHeader(),
            footer: (currentPage, pageCount) => this.createFooter(currentPage, pageCount),
            content: content,
            styles: this.getStyles(),
            defaultStyle: {
                font: defaultFont,
                fontSize: 10,
                color: '#333333'
            },
            info: {
                title: `${data.title} - Itinerary`,
                author: 'Aitinerary',
                subject: `Travel itinerary for ${data.destination}`,
                creator: 'Aitinerary'
            }
        };

        const filename = `${data.title.replace(/[^a-z0-9]/gi, '_')}_itinerary.pdf`;

        return new Promise((resolve, reject) => {
            try {
                pdfMake.createPdf(docDefinition).download(filename, () => {
                    resolve();
                });
            } catch (error) {
                console.error('PDF generation error:', error);
                reject(error);
            }
        });
    }
};
