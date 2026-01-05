%% PhotonPath MATLAB SDK
% Simple MATLAB client for the PhotonPath API
%
% Installation:
%   - Download this file to your MATLAB path
%   - Requires MATLAB R2016b+ with webread/webwrite
%
% Usage:
%   pp = PhotonPathClient('your_api_key');
%   props = pp.get_tissue('brain_gray_matter', 630);
%   disp(['Penetration: ' num2str(props.derived.penetration_depth_mm) ' mm']);
%
% Author: PhotonPath
% Version: 2.0.0
% License: MIT

classdef PhotonPathClient < handle
    
    properties
        api_key
        base_url
        timeout
    end
    
    methods
        function obj = PhotonPathClient(api_key, base_url)
            % Constructor
            if nargin < 1
                api_key = 'demo_key_12345';
            end
            if nargin < 2
                base_url = 'http://localhost:8000';
            end
            
            obj.api_key = api_key;
            obj.base_url = base_url;
            obj.timeout = 30;
        end
        
        %% === INTERNAL METHODS ===
        function result = get_request(obj, endpoint, params)
            % Make GET request
            if nargin < 3
                params = struct();
            end
            
            url = [obj.base_url endpoint];
            
            % Add query parameters
            fields = fieldnames(params);
            if ~isempty(fields)
                url = [url '?'];
                for i = 1:length(fields)
                    if i > 1
                        url = [url '&'];
                    end
                    val = params.(fields{i});
                    if isnumeric(val)
                        val = num2str(val);
                    end
                    url = [url fields{i} '=' val];
                end
            end
            
            options = weboptions('HeaderFields', {'X-API-Key', obj.api_key}, ...
                                 'Timeout', obj.timeout);
            result = webread(url, options);
        end
        
        function result = post_request(obj, endpoint, data)
            % Make POST request
            url = [obj.base_url endpoint];
            options = weboptions('HeaderFields', {'X-API-Key', obj.api_key}, ...
                                 'MediaType', 'application/json', ...
                                 'Timeout', obj.timeout);
            result = webwrite(url, data, options);
        end
        
        %% === HEALTH & INFO ===
        function result = health(obj)
            % Check API health
            result = obj.get_request('/health');
        end
        
        function result = info(obj)
            % Get API info
            result = obj.get_request('/');
        end
        
        %% === TISSUES ===
        function result = list_tissues(obj, category, search)
            % List available tissues
            params = struct();
            if nargin >= 2 && ~isempty(category)
                params.category = category;
            end
            if nargin >= 3 && ~isempty(search)
                params.search = search;
            end
            result = obj.get_request('/v2/tissues', params);
        end
        
        function result = get_tissue(obj, tissue_id, wavelength)
            % Get tissue optical properties
            params = struct('wavelength', wavelength);
            result = obj.get_request(['/v2/tissues/' tissue_id], params);
        end
        
        function result = get_tissue_spectrum(obj, tissue_id, wl_min, wl_max, step)
            % Get full spectrum
            if nargin < 3, wl_min = 400; end
            if nargin < 4, wl_max = 900; end
            if nargin < 5, step = 10; end
            
            params = struct('wl_min', wl_min, 'wl_max', wl_max, 'step', step);
            result = obj.get_request(['/v2/tissues/' tissue_id '/spectrum'], params);
        end
        
        function result = compare_tissues(obj, tissue_ids, wavelength)
            % Compare multiple tissues
            % tissue_ids should be a cell array of strings
            params = struct('tissue_ids', strjoin(tissue_ids, ','), ...
                           'wavelength', wavelength);
            result = obj.get_request('/v2/tissues/compare', params);
        end
        
        %% === OPTOGENETICS ===
        function result = list_opsins(obj, opsin_type)
            % List available opsins
            params = struct();
            if nargin >= 2 && ~isempty(opsin_type)
                params.opsin_type = opsin_type;
            end
            result = obj.get_request('/v2/optogenetics/opsins', params);
        end
        
        function result = get_opsin(obj, opsin_id)
            % Get opsin details
            result = obj.get_request(['/v2/optogenetics/opsins/' opsin_id]);
        end
        
        function result = optogenetics_power(obj, opsin_id, depth_mm, tissue_id, fiber_diameter_um, fiber_NA)
            % Calculate required power for optogenetics
            if nargin < 4, tissue_id = 'brain_gray_matter'; end
            if nargin < 5, fiber_diameter_um = 200; end
            if nargin < 6, fiber_NA = 0.39; end
            
            params = struct('opsin_id', opsin_id, ...
                           'target_depth_mm', depth_mm, ...
                           'tissue_id', tissue_id, ...
                           'fiber_diameter_um', fiber_diameter_um, ...
                           'fiber_NA', fiber_NA);
            result = obj.get_request('/v2/optogenetics/power-calculator', params);
        end
        
        function result = recommend_opsin(obj, application, depth_mm, max_power_mW, tissue_id)
            % Get opsin recommendation
            if nargin < 2, application = 'excitatory'; end
            if nargin < 3, depth_mm = 2.0; end
            if nargin < 4, max_power_mW = 30; end
            if nargin < 5, tissue_id = 'brain_gray_matter'; end
            
            params = struct('application', application, ...
                           'target_depth_mm', depth_mm, ...
                           'max_power_mW', max_power_mW, ...
                           'tissue_id', tissue_id);
            result = obj.get_request('/v2/optogenetics/recommend', params);
        end
        
        %% === CALCIUM IMAGING ===
        function result = list_calcium_indicators(obj)
            % List calcium indicators
            result = obj.get_request('/v2/calcium/indicators');
        end
        
        function result = predict_calcium_signal(obj, indicator_id, depth_mm, power_mW, NA, tissue_id)
            % Predict calcium signal quality
            if nargin < 4, power_mW = 10; end
            if nargin < 5, NA = 0.8; end
            if nargin < 6, tissue_id = 'brain_gray_matter'; end
            
            params = struct('indicator_id', indicator_id, ...
                           'depth_mm', depth_mm, ...
                           'power_mW', power_mW, ...
                           'NA', NA, ...
                           'tissue_id', tissue_id);
            result = obj.get_request('/v2/calcium/signal-prediction', params);
        end
        
        %% === THERMAL SAFETY ===
        function result = check_thermal_safety(obj, power_mW, wavelength, spot_mm, application, tissue_id)
            % Check thermal safety
            if nargin < 3, wavelength = 470; end
            if nargin < 4, spot_mm = 0.2; end
            if nargin < 5, application = 'chronic'; end
            if nargin < 6, tissue_id = 'brain_gray_matter'; end
            
            params = struct('power_mW', power_mW, ...
                           'wavelength', wavelength, ...
                           'spot_mm', spot_mm, ...
                           'application', application, ...
                           'tissue_id', tissue_id);
            result = obj.get_request('/v2/thermal/check', params);
        end
        
        function result = pulsed_thermal(obj, peak_power_mW, pulse_ms, freq_Hz, duration_s)
            % Analyze pulsed thermal effects
            if nargin < 5, duration_s = 1.0; end
            
            params = struct('peak_power_mW', peak_power_mW, ...
                           'pulse_ms', pulse_ms, ...
                           'freq_Hz', freq_Hz, ...
                           'duration_s', duration_s);
            result = obj.get_request('/v2/thermal/pulsed', params);
        end
        
        %% === MONTE CARLO ===
        function result = simulate_quick(obj, tissue_id, wavelength, n_photons)
            % Quick Monte Carlo simulation
            if nargin < 2, tissue_id = 'brain_gray_matter'; end
            if nargin < 3, wavelength = 630; end
            if nargin < 4, n_photons = 1000; end
            
            params = struct('tissue_id', tissue_id, ...
                           'wavelength', wavelength, ...
                           'n_photons', n_photons);
            result = obj.get_request('/v2/simulate/quick', params);
        end
        
        %% === PROTOCOLS ===
        function result = generate_protocol(obj, opsin, region, depth_mm, species, chronic)
            % Generate optogenetics protocol
            if nargin < 2, opsin = 'ChR2'; end
            if nargin < 3, region = 'cortex'; end
            if nargin < 4, depth_mm = 1.0; end
            if nargin < 5, species = 'mouse'; end
            if nargin < 6, chronic = true; end
            
            params = struct('opsin', opsin, ...
                           'region', region, ...
                           'depth_mm', depth_mm, ...
                           'species', species, ...
                           'chronic', chronic);
            result = obj.get_request('/v2/protocols/optogenetics', params);
        end
    end
    
    methods (Static)
        function demo()
            % Run demo
            disp('PhotonPath MATLAB SDK Demo');
            disp('==========================');
            
            pp = PhotonPathClient();
            
            % Health check
            h = pp.health();
            fprintf('\n✓ Connected to API\n');
            fprintf('  Tissues: %d\n', h.databases.tissues);
            fprintf('  Opsins: %d\n', h.databases.opsins);
            
            % Get tissue properties
            props = pp.get_tissue('brain_gray_matter', 630);
            fprintf('\nBrain @ 630nm:\n');
            fprintf('  μa = %f mm^-1\n', props.optical_properties.mu_a);
            fprintf('  Penetration = %.3f mm\n', props.derived.penetration_depth_mm);
            
            % Calculate power
            power = pp.optogenetics_power('ChR2', 2.0);
            fprintf('\nChR2 @ 2mm depth:\n');
            fprintf('  Required power = %.2f mW\n', power.calculation.required_power_mW);
            
            disp(' ');
            disp('✓ SDK working correctly!');
        end
    end
end
