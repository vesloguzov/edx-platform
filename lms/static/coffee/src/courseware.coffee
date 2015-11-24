class @Courseware
  @root_path_prefix: ''

  constructor: ->
    Courseware.root_path_prefix = $("meta[name='root_path_prefix']").attr('content')
    Logger.bind()
    @render()

  @start: ->
    new Courseware

  render: ->
    XBlock.initializeBlocks($('.course-content'))
    $('.course-content .histogram').each ->
      id = $(this).attr('id').replace(/histogram_/, '')
      try
        histg = new Histogram id, $(this).data('histogram')
      catch error
        histg = error
        if console?
          console.log(error)
      return histg
