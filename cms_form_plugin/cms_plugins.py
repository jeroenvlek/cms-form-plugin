from cms.plugin_base import CMSPluginBase
from cms.plugin_pool import plugin_pool

from models import FormPlugin

from django.utils.translation import ugettext as _
from django.utils.module_loading import import_by_path
from django.core.urlresolvers import reverse
from django.shortcuts import get_object_or_404
from django.http import Http404, HttpResponseRedirect
from django.core.exceptions import ImproperlyConfigured

import pickle


class CMSFormPlugin(CMSPluginBase):
    model = FormPlugin
    name = _("Form")
    render_template = "form/form.html"

    @classmethod
    def form_post(cls, request, instance_id):
        '''
        Handles all POST requests from FormPlugin's form_class
        instances. If the form is valid, it calls the form's
        save method. If the form is not valid, it stores the
        form's instance inside the session with name
        format invalid_form_%(instance_id) where instance_id
        is the id of the FormPlugin instance (to support multiple
        forms on one page)
        '''

        if not hasattr(request, 'session'):
            raise ImproperlyConfigured('Sessions must be enabled')

        instance = get_object_or_404(
            FormPlugin, pk = int(instance_id))

        form = import_by_path(instance.form_class)
        response = None

        if request.method == 'POST':
            form = form(request.POST)
            
            if form.is_valid():
                if hasattr(form, 'save'):
                    if hasattr(form.save, '__call__'):
                        form.save()
                response = HttpResponseRedirect(
                    request.POST['success_url']
                )
                if 'invalid_form_%s' % instance_id in request.session:
                    del request.session[
                        'invalid_form_%s' % instance_id]

                return response

            if request.POST['invalid_url']:
                response = HttpResponseRedirect(
                    request.POST['invalid_url']
                )
                
            # store the invalid form in the session
            form.invalid_url = request.POST['invalid_url']
            request.session[
                'invalid_form_%s' % instance_id] = pickle.dumps(form)

        if not response:
            response = HttpResponseRedirect(
                request.META['HTTP_REFERER'] # back to the referer
            )
        return response

    def render(self, context, instance, placeholder):
        '''
        Renders the plugin instance. If there is an
        instance of the plugin's form_class in the session w name
        invalid_form_%(instance_id) we assume the form was
        submitted before but rendered invalid.
        '''

        request = context['request']
        
        if not hasattr(request, 'session'):
            raise ImproperlyConfigured('Sessions must be enabled')
        
        form_class = import_by_path(instance.form_class)
        form = request.session.get(
            'invalid_form_%s' % instance.id, None)

        if form is None:
            form = form_class()
        else:
            form = pickle.loads(form)
        
        context['form'] = form
        
        context.update({
            'post_to_url': reverse(
                'form_post', args=(instance.id,)
            ),
            'success_url': instance.success_url,
            'submit_caption': instance.submit_caption,
        })
        return context

        
plugin_pool.register_plugin(CMSFormPlugin)