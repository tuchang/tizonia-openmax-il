/**
 * Copyright (C) 2011-2019 Aratelia Limited - Juan A. Rubio
 *
 * This file is part of Tizonia
 *
 * Tizonia is free software: you can redistribute it and/or modify it under the
 * terms of the GNU Lesser General Public License as published by the Free
 * Software Foundation, either version 3 of the License, or (at your option)
 * any later version.
 *
 * Tizonia is distributed in the hope that it will be useful, but WITHOUT ANY
 * WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
 * FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for
 * more details.
 *
 * You should have received a copy of the GNU Lesser General Public License
 * along with Tizonia.  If not, see <http://www.gnu.org/licenses/>.
 */

/**
 * @file   tizflacport.h
 * @author Juan A. Rubio <juan.rubio@aratelia.com>
 *
 * @brief  FLAC port class
 *
 *
 */

#ifndef TIZFLACPORT_H
#define TIZFLACPORT_H

#ifdef __cplusplus
extern "C" {
#endif

void *
tiz_flacport_class_init (void * ap_tos, void * ap_hdl);
void *
tiz_flacport_init (void * ap_tos, void * ap_hdl);

#ifdef __cplusplus
}
#endif

#endif /* TIZFLACPORT_H */
